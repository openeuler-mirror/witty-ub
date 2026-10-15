/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include <gtest/gtest.h>

#include <sys/stat.h>

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <memory>
#include <optional>
#include <regex>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "lcne_common.h"
#include "lcne_data_handler.h"
#include "logger.h"

namespace lcne::common {
// lcne_common.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
bool MkdirRecursive(const std::string &dir);
LcneResult GenerateNotifyReqBody(std::string &reqBody);
} // namespace lcne::common

namespace {

// 被测实现中大量使用 LOG_ERROR/LOG_INFO，log4cplus 必须先初始化
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每个用例独立的临时目录，析构时清理
class TempDir {
public:
    TempDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_lcne_test_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir() { std::filesystem::remove_all(dir_); }

    const std::filesystem::path &Path() const { return dir_; }

private:
    std::filesystem::path dir_;
};

// 解析 XML 字符串并返回根元素
tinyxml2::XMLElement *ParseRoot(const std::string &xml)
{
    static tinyxml2::XMLDocument doc;
    EXPECT_EQ(doc.Parse(xml.c_str()), tinyxml2::XML_SUCCESS);
    return doc.RootElement();
}

} // namespace

// ---------------------------------------------------------------------------
// lcne_common：纯工具函数
// ---------------------------------------------------------------------------

TEST(LcneCommon, GetHostnameReturnsNonEmpty)
{
    // 本机主机名应可获取
    EXPECT_FALSE(lcne::common::GetHostname().empty());
}

TEST(LcneCommon, StringToUpperConvertsAll)
{
    EXPECT_EQ(lcne::common::StringToUpper("abc-DEF9"), "ABC-DEF9");
    EXPECT_EQ(lcne::common::StringToUpper(""), "");
}

TEST(LcneCommon, IsSpecialIpRegexIsBroken)
{
    // 生产问题（勿修）：正则 "169\.254\..*)" 中 ')' 未闭合，
    // std::regex 构造直接抛出 std::regex_error，任何输入都无法完成匹配。
    EXPECT_THROW(lcne::common::IsSpecialIp("127.0.0.1"), std::regex_error);
    EXPECT_THROW(lcne::common::IsSpecialIp("192.168.1.1"), std::regex_error);
}

TEST(LcneCommon, GetNodeIpInfosPropagatesRegexError)
{
    // /proc/net/fib_trie 必然包含 127.0.0.1，因此 IsSpecialIp 的异常会传播出来
    std::vector<std::string> ips;
    EXPECT_THROW(lcne::common::GetNodeIpInfos(ips), std::regex_error);
}

TEST(LcneCommon, CheckXMLRejectsInvalidElements)
{
    // 空指针 / 无文本 / 空文本均拒绝
    EXPECT_EQ(lcne::common::checkXML(nullptr), lcne::LCNE_FAIL);
    EXPECT_EQ(lcne::common::checkXML(ParseRoot("<a/>")), lcne::LCNE_FAIL);
    EXPECT_EQ(lcne::common::checkXML(ParseRoot("<a></a>")), lcne::LCNE_FAIL);
    EXPECT_EQ(lcne::common::checkXML(ParseRoot("<a>text</a>")), lcne::LCNE_SUCCESS);
}

TEST(LcneCommon, GetTextAsString)
{
    // 空元素指针返回 FAIL
    std::string out;
    EXPECT_EQ(lcne::common::getTextAsString(nullptr, out), lcne::LCNE_FAIL);

    // 正常元素：输出文本
    EXPECT_EQ(lcne::common::getTextAsString(ParseRoot("<a>hello</a>"), out), lcne::LCNE_SUCCESS);
    EXPECT_EQ(out, "hello");
}

TEST(LcneCommon, ConvertTextToUint)
{
    uint32_t value = 0;
    // 正常数值
    EXPECT_EQ(lcne::common::convertTextToUint<uint32_t>(ParseRoot("<a>42</a>"), value), lcne::LCNE_SUCCESS);
    EXPECT_EQ(value, 42u);

    // 非数字：stoul 抛 invalid_argument
    EXPECT_EQ(lcne::common::convertTextToUint<uint32_t>(ParseRoot("<a>abc</a>"), value), lcne::LCNE_FAIL);
    // 超出 uint32 范围
    EXPECT_EQ(lcne::common::convertTextToUint<uint32_t>(ParseRoot("<a>4294967296</a>"), value), lcne::LCNE_FAIL);
    // 负数被 stoul 包装成巨值后同样超范围
    EXPECT_EQ(lcne::common::convertTextToUint<uint32_t>(ParseRoot("<a>-5</a>"), value), lcne::LCNE_FAIL);
    // 无文本元素：checkXML 失败（元素本身非空，安全）
    EXPECT_EQ(lcne::common::convertTextToUint<uint32_t>(ParseRoot("<a/>"), value), lcne::LCNE_FAIL);
}

TEST(LcneCommon, ConvertTextToOptionalUint)
{
    std::optional<uint32_t> value;
    // 正常数值
    EXPECT_EQ(lcne::common::ConvertTextToOptionalUint<uint32_t>(ParseRoot("<a>7</a>"), value), lcne::LCNE_SUCCESS);
    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(*value, 7u);

    // 非数字视为"无值"：返回 SUCCESS 且 optional 为空
    value.reset();
    EXPECT_EQ(lcne::common::ConvertTextToOptionalUint<uint32_t>(ParseRoot("<a>N/A</a>"), value), lcne::LCNE_SUCCESS);
    EXPECT_FALSE(value.has_value());

    // 超范围仍失败
    EXPECT_EQ(lcne::common::ConvertTextToOptionalUint<uint32_t>(ParseRoot("<a>4294967296</a>"), value),
              lcne::LCNE_FAIL);
    // 无文本元素失败
    EXPECT_EQ(lcne::common::ConvertTextToOptionalUint<uint32_t>(ParseRoot("<a/>"), value), lcne::LCNE_FAIL);
}

TEST(LcneCommon, GetElementWalksPath)
{
    // 按路径逐层查找子元素。
    // 生产缺陷：getElement 返回指向其函数内部局部 XMLDocument 的指针，文档随返回被析构，
    // 指针即刻悬空（use-after-free，已报告勿修）——悬空内存上 GetText() 读到 NULL 即症状。
    // 因此这里只比较返回指针的值，不对成功路径的结果做解引用断言。
    std::string xml = "<top><mid><leaf>value</leaf></mid></top>";
    auto *leaf = lcne::common::getElement(xml, "mid", "leaf");
    EXPECT_NE(leaf, nullptr);

    // 路径不存在：返回 nullptr
    EXPECT_EQ(lcne::common::getElement(xml, "nope"), nullptr);
    // 多级路径中第一级缺失：中途 break
    EXPECT_EQ(lcne::common::getElement(xml, "nope", "leaf"), nullptr);

    // 非法 XML：解析失败返回 nullptr
    std::string bad = "<top><unclosed></top>";
    EXPECT_EQ(lcne::common::getElement(bad, "mid"), nullptr);
}

TEST(LcneCommon, GenerateNotifyReqBody)
{
    std::string body;
    EXPECT_EQ(lcne::common::GenerateNotifyReqBody(body), lcne::LCNE_SUCCESS);
    EXPECT_NE(body.find("<create-subscription"), std::string::npos);
    EXPECT_NE(body.find("<ip>127.0.0.1</ip>"), std::string::npos);
    EXPECT_NE(body.find("<port>34256</port>"), std::string::npos);
    EXPECT_NE(body.find("<url>/topolink/change</url>"), std::string::npos);
}

TEST(LcneCommon, HttpFunctionsFailWithoutServer)
{
    // 127.0.0.1:34256 无服务监听：连接被拒绝，两个 HTTP 入口都返回失败
    std::string body;
    EXPECT_EQ(lcne::common::GetHttpData(body, "/restconf/data/test"), lcne::LCNE_FAIL);
    EXPECT_EQ(lcne::common::PostLinkInfoNotify(), lcne::LCNE_FAIL);
}

TEST(LcneCommon, XmlHttpHandlersFailWithoutServer)
{
    // getXML* 系列依赖 GetHttpData，无服务时统一走失败路径
    std::map<lcne::handler::LcneKey, lcne::handler::XmlNode> nodes;
    EXPECT_EQ(lcne::handler::getXMLNodes("/nodes", nodes), lcne::LCNE_FAIL);

    std::map<lcne::handler::LcneKey, lcne::handler::XmlIouInfo> ious;
    EXPECT_EQ(lcne::handler::getXMLIouInfo("/iou-infos", ious), lcne::LCNE_FAIL);

    std::map<lcne::handler::LcneKey, lcne::handler::XmlAddress> addresses;
    EXPECT_EQ(lcne::handler::getXMLAddress("/addresses", addresses), lcne::LCNE_FAIL);

    std::shared_ptr<lcne::handler::XmlLogicEntity> entity;
    EXPECT_EQ(lcne::handler::GetXmlLogicEntities("/logic-entities", entity), lcne::LCNE_FAIL);
    EXPECT_EQ(entity, nullptr);
}

TEST(LcneCommon, MkdirRecursive)
{
    // 已存在目录直接成功
    TempDir dir;
    EXPECT_TRUE(lcne::common::MkdirRecursive(dir.Path().string()));

    // 嵌套目录递归创建
    std::string nested = (dir.Path() / "a/b/c").string();
    EXPECT_TRUE(lcne::common::MkdirRecursive(nested));
    EXPECT_TRUE(std::filesystem::is_directory(nested));

    // 父目录只读时创建失败（非 root 环境）
    std::string ro = (dir.Path() / "ro").string();
    ASSERT_TRUE(std::filesystem::create_directory(ro));
    ASSERT_EQ(::chmod(ro.c_str(), 0555), 0);
    EXPECT_FALSE(lcne::common::MkdirRecursive(ro + "/sub"));
    ::chmod(ro.c_str(), 0755);
}

TEST(LcneCommon, SaveIpToConfigFileFailsWithoutRoot)
{
    // /etc/witty-ub 不存在且 /etc 对普通用户不可写：目录创建失败
    EXPECT_EQ(lcne::common::SaveIpToConfigFile("192.168.1.100"), lcne::LCNE_FAIL);
}

// ---------------------------------------------------------------------------
// lcne_data_handler：XML 端口解析
// ---------------------------------------------------------------------------

TEST(LcneDataHandler, GetNodePhysicalPortsParsesPorts)
{
    // 注意：每个 physical-port 必须带全 remote-* 子元素，缺失会在实现中解引用空指针
    auto *element = ParseRoot(
        "<physical-ports>"
        "<physical-port><physical-port-id>1</physical-port-id><physical-port-status>UP</physical-port-status>"
        "<remote-slot>3</remote-slot><remote-ubpu>4</remote-ubpu><remote-iou>5</remote-iou>"
        "<remote-physical-port-id>6</remote-physical-port-id></physical-port>"
        "<physical-port><physical-port-id>2</physical-port-id><physical-port-status>DOWN</physical-port-status>"
        "<remote-slot>N/A</remote-slot><remote-ubpu>N/A</remote-ubpu><remote-iou>N/A</remote-iou>"
        "<remote-physical-port-id>N/A</remote-physical-port-id></physical-port>"
        "</physical-ports>");
    std::unordered_map<uint32_t, lcne::handler::XmlPhysicalPort> ports;
    EXPECT_EQ(lcne::handler::getNodePhysicalPorts(element, ports), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ports.size(), 2u);

    const auto &first = ports.at(1u);
    EXPECT_EQ(first.physicalPortStatus, "UP");
    ASSERT_TRUE(first.remoteSlot.has_value());
    EXPECT_EQ(*first.remoteSlot, 3u);
    ASSERT_TRUE(first.remotePhysicalPortId.has_value());
    EXPECT_EQ(*first.remotePhysicalPortId, 6u);

    // 非数字 remote 值解析为空 optional
    const auto &second = ports.at(2u);
    EXPECT_FALSE(second.remoteSlot.has_value());
    EXPECT_FALSE(second.remoteUbpu.has_value());
}

TEST(LcneDataHandler, GetNodePhysicalPortsRejectsBadPort)
{
    // 端口 id 非数字
    auto *badId = ParseRoot(
        "<physical-ports><physical-port><physical-port-id>abc</physical-port-id>"
        "<physical-port-status>UP</physical-port-status><remote-slot>1</remote-slot><remote-ubpu>1</remote-ubpu>"
        "<remote-iou>1</remote-iou><remote-physical-port-id>1</remote-physical-port-id></physical-port>"
        "</physical-ports>");
    std::unordered_map<uint32_t, lcne::handler::XmlPhysicalPort> ports;
    EXPECT_EQ(lcne::handler::getNodePhysicalPorts(badId, ports), lcne::LCNE_FAIL);

    // 端口状态元素无文本
    auto *badStatus = ParseRoot(
        "<physical-ports><physical-port><physical-port-id>1</physical-port-id><physical-port-status/>"
        "<remote-slot>1</remote-slot><remote-ubpu>1</remote-ubpu>"
        "<remote-iou>1</remote-iou><remote-physical-port-id>1</remote-physical-port-id></physical-port>"
        "</physical-ports>");
    EXPECT_EQ(lcne::handler::getNodePhysicalPorts(badStatus, ports), lcne::LCNE_FAIL);
}

TEST(LcneDataHandler, GetNodePhysicalPortsHandlesNullAndEmpty)
{
    // 空元素指针
    std::unordered_map<uint32_t, lcne::handler::XmlPhysicalPort> ports;
    EXPECT_EQ(lcne::handler::getNodePhysicalPorts(nullptr, ports), lcne::LCNE_FAIL);

    // 无子端口：成功且映射为空
    auto *empty = ParseRoot("<physical-ports/>");
    EXPECT_EQ(lcne::handler::getNodePhysicalPorts(empty, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());
}

TEST(LcneDataHandler, GetAddressPhysicalPortsParsesPorts)
{
    auto *element = ParseRoot(
        "<physical-ports>"
        "<physical-port><physical-port-id>7</physical-port-id><port-cna>pcna</port-cna>"
        "<bus-port-cna>bcna</bus-port-cna></physical-port>"
        "</physical-ports>");
    std::unordered_map<uint32_t, lcne::handler::XmlAddressPhysicalPort> ports;
    EXPECT_EQ(lcne::handler::getAddressPhysicalPorts(element, ports), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ports.size(), 1u);
    EXPECT_EQ(ports.at(7u).portCna, "pcna");
    EXPECT_EQ(ports.at(7u).busPortCna, "bcna");
}

TEST(LcneDataHandler, GetAddressPhysicalPortsRejectsBadInput)
{
    std::unordered_map<uint32_t, lcne::handler::XmlAddressPhysicalPort> ports;
    // 空元素指针
    EXPECT_EQ(lcne::handler::getAddressPhysicalPorts(nullptr, ports), lcne::LCNE_FAIL);
    // 端口 id 非数字
    auto *badId = ParseRoot("<physical-ports><physical-port><physical-port-id>x</physical-port-id>"
                            "<port-cna>a</port-cna><bus-port-cna>b</bus-port-cna></physical-port>"
                            "</physical-ports>");
    EXPECT_EQ(lcne::handler::getAddressPhysicalPorts(badId, ports), lcne::LCNE_FAIL);
    // port-cna 无文本
    auto *badCna = ParseRoot("<physical-ports><physical-port><physical-port-id>1</physical-port-id>"
                             "<port-cna/><bus-port-cna>b</bus-port-cna></physical-port>"
                             "</physical-ports>");
    EXPECT_EQ(lcne::handler::getAddressPhysicalPorts(badCna, ports), lcne::LCNE_FAIL);
    // 空容器元素
    auto *empty = ParseRoot("<physical-ports/>");
    EXPECT_EQ(lcne::handler::getAddressPhysicalPorts(empty, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());
}

// ---------------------------------------------------------------------------
// lcne_data_handler：拓扑对象生成
// ---------------------------------------------------------------------------

namespace {

lcne::handler::XmlPhysicalPort MakeNodePort(uint32_t id, const std::string &status = "UP")
{
    return lcne::handler::XmlPhysicalPort(id, status, std::nullopt, std::nullopt, std::nullopt, std::nullopt);
}

} // namespace

TEST(LcneDataHandler, GenerateLcneNodes)
{
    std::map<lcne::handler::LcneKey, lcne::handler::XmlNode> xmlNodes;
    std::string ubpuType = "CPU";
    lcne::handler::XmlNode node(1, 2, 3, ubpuType, {});
    xmlNodes[std::make_tuple(1u, 2u, 3u)] = node;

    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    EXPECT_EQ(lcne::handler::generateLcneNodes(xmlNodes, nodes), lcne::LCNE_SUCCESS);
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0]->deviceId, 1u);
    EXPECT_EQ(nodes[0]->slotId, 1u);
    EXPECT_EQ(nodes[0]->chipNum, 2u);
    EXPECT_EQ(nodes[0]->dieNum, 3u);
    EXPECT_EQ(nodes[0]->chipType, topology::node::ChipType::CPU);
    EXPECT_EQ(nodes[0]->hostname, lcne::common::GetHostname());

    // 空输入：成功且无输出
    std::vector<std::shared_ptr<topology::node::Node>> none;
    EXPECT_EQ(lcne::handler::generateLcneNodes({}, none), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(none.empty());
}

TEST(LcneDataHandler, GenerateLcneUBController)
{
    using lcne::handler::LcneKey;
    using lcne::handler::XmlNode;
    using lcne::handler::XmlIouInfo;
    using lcne::handler::XmlPhysicalPort;

    // 节点带两个物理端口
    std::unordered_map<uint32_t, XmlPhysicalPort> ports;
    ports[1u] = MakeNodePort(1u);
    ports[2u] = MakeNodePort(2u);
    std::string ubpuType = "NPU";
    std::map<LcneKey, XmlNode> xmlNodes;
    xmlNodes[std::make_tuple(1u, 2u, 3u)] = XmlNode(1, 2, 3, ubpuType, ports);

    std::map<LcneKey, XmlIouInfo> xmlIous;
    xmlIous[std::make_tuple(1u, 2u, 3u)] = XmlIouInfo("guid", "eid", 1, 2, 3, "cna", "normal");
    auto logic = std::make_shared<lcne::handler::XmlLogicEntity>("online");

    std::vector<std::shared_ptr<topology::node::UbController>> controllers;
    EXPECT_EQ(lcne::handler::generateLcneUBController(xmlNodes, xmlIous, logic, controllers), lcne::LCNE_SUCCESS);
    ASSERT_EQ(controllers.size(), 1u);
    const auto &ubc = *controllers[0];
    EXPECT_EQ(ubc.dieGuid, "guid");
    EXPECT_EQ(ubc.ubcEid, "eid");
    EXPECT_EQ(ubc.deviceId, 1u);
    EXPECT_EQ(ubc.chipId, 2u);
    EXPECT_EQ(ubc.dieId, 3u);
    EXPECT_EQ(ubc.primaryCna, "cna");
    // die 状态与 ubc 状态大小写不敏感
    EXPECT_EQ(ubc.dieState, topology::node::DieState::NORMAL);
    EXPECT_EQ(ubc.ubcState, topology::node::UbCState::ONLINE);
    // 端口 id 集合来自节点（无序，拷贝排序后比较）
    std::vector<uint32_t> expectPorts = {1u, 2u};
    std::vector<uint32_t> actualPorts = ubc.portIds;
    std::sort(actualPorts.begin(), actualPorts.end());
    EXPECT_EQ(actualPorts, expectPorts);
}

TEST(LcneDataHandler, GenerateLcneUBControllerMissingNodeContinues)
{
    // iou 信息没有对应节点：跳过该条但整体成功
    std::map<lcne::handler::LcneKey, lcne::handler::XmlIouInfo> xmlIous;
    xmlIous[std::make_tuple(9u, 9u, 9u)] =
        lcne::handler::XmlIouInfo("g", "e", 9, 9, 9, "c", "normal");
    auto logic = std::make_shared<lcne::handler::XmlLogicEntity>("online");

    std::vector<std::shared_ptr<topology::node::UbController>> controllers;
    EXPECT_EQ(lcne::handler::generateLcneUBController({}, xmlIous, logic, controllers), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(controllers.empty());
}

TEST(LcneDataHandler, GenerateLcneUBControllerBadStatesFail)
{
    using lcne::handler::LcneKey;
    using lcne::handler::XmlNode;
    using lcne::handler::XmlIouInfo;

    std::string ubpuType = "CPU";
    std::map<LcneKey, XmlNode> xmlNodes;
    xmlNodes[std::make_tuple(1u, 2u, 3u)] = XmlNode(1, 2, 3, ubpuType, {});
    std::map<LcneKey, XmlIouInfo> xmlIous;
    xmlIous[std::make_tuple(1u, 2u, 3u)] = XmlIouInfo("g", "e", 1, 2, 3, "c", "weird");
    auto logic = std::make_shared<lcne::handler::XmlLogicEntity>("online");

    // 未知 die 状态
    std::vector<std::shared_ptr<topology::node::UbController>> controllers;
    EXPECT_EQ(lcne::handler::generateLcneUBController(xmlNodes, xmlIous, logic, controllers), lcne::LCNE_FAIL);

    // 未知 ubc 状态
    xmlIous[std::make_tuple(1u, 2u, 3u)] = XmlIouInfo("g", "e", 1, 2, 3, "c", "normal");
    auto badLogic = std::make_shared<lcne::handler::XmlLogicEntity>("weird");
    EXPECT_EQ(lcne::handler::generateLcneUBController(xmlNodes, xmlIous, badLogic, controllers), lcne::LCNE_FAIL);

    // 空输入：成功且无输出
    EXPECT_EQ(lcne::handler::generateLcneUBController({}, {}, logic, controllers), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(controllers.empty());
}

TEST(LcneDataHandler, GenerateLcnePort)
{
    using lcne::handler::LcneKey;
    using lcne::handler::XmlNode;
    using lcne::handler::XmlAddress;
    using lcne::handler::XmlAddressPhysicalPort;
    using lcne::handler::XmlPhysicalPort;

    // 节点端口 7 状态 UP，带远端信息
    std::unordered_map<uint32_t, XmlPhysicalPort> nodePorts;
    nodePorts[7u] = XmlPhysicalPort(7u, "UP", std::make_optional(3u), std::make_optional(4u),
                                    std::make_optional(5u), std::make_optional(8u));
    std::string ubpuType = "CPU";
    std::map<LcneKey, XmlNode> xmlNodes;
    xmlNodes[std::make_tuple(1u, 2u, 3u)] = XmlNode(1, 2, 3, ubpuType, nodePorts);

    std::unordered_map<uint32_t, XmlAddressPhysicalPort> addrPorts;
    addrPorts[7u] = XmlAddressPhysicalPort(7u, "port-cna", "bus-cna");
    std::map<LcneKey, XmlAddress> xmlAddresses;
    xmlAddresses[std::make_tuple(1u, 2u, 3u)] = XmlAddress(1, 2, 3, "primary-cna", addrPorts);

    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(lcne::handler::generateLcnePort(xmlNodes, xmlAddresses, ports), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ports.size(), 1u);
    const auto &port = *ports[0];
    EXPECT_EQ(port.portId, 7u);
    EXPECT_EQ(port.portCna, "port-cna");
    EXPECT_EQ(port.primaryCna, "primary-cna");
    EXPECT_EQ(port.deviceId, 1u);
    EXPECT_EQ(port.portState, topology::node::PortState::UP);
    ASSERT_TRUE(port.remoteSlotId.has_value());
    EXPECT_EQ(*port.remoteSlotId, 3u);
    ASSERT_TRUE(port.remoteIouId.has_value());
    EXPECT_EQ(*port.remoteIouId, 5u);
}

TEST(LcneDataHandler, GenerateLcnePortSkipsMissingEntries)
{
    using lcne::handler::LcneKey;
    using lcne::handler::XmlAddress;
    using lcne::handler::XmlAddressPhysicalPort;

    // 地址对应的节点不存在：跳过
    std::unordered_map<uint32_t, XmlAddressPhysicalPort> addrPorts;
    addrPorts[1u] = XmlAddressPhysicalPort(1u, "c", "b");
    std::map<LcneKey, XmlAddress> xmlAddresses;
    xmlAddresses[std::make_tuple(9u, 9u, 9u)] = XmlAddress(9, 9, 9, "p", addrPorts);

    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(lcne::handler::generateLcnePort({}, xmlAddresses, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());

    // 节点存在但缺少对应物理端口：跳过
    std::string ubpuType = "CPU";
    std::map<LcneKey, lcne::handler::XmlNode> xmlNodes;
    xmlNodes[std::make_tuple(9u, 9u, 9u)] = lcne::handler::XmlNode(9, 9, 9, ubpuType, {});
    ports.clear();
    EXPECT_EQ(lcne::handler::generateLcnePort(xmlNodes, xmlAddresses, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());
}

TEST(LcneDataHandler, GenerateLcnePortBadStateFails)
{
    using lcne::handler::LcneKey;
    using lcne::handler::XmlNode;
    using lcne::handler::XmlAddress;
    using lcne::handler::XmlAddressPhysicalPort;
    using lcne::handler::XmlPhysicalPort;

    // 端口状态无法映射：整体失败
    std::unordered_map<uint32_t, XmlPhysicalPort> nodePorts;
    nodePorts[1u] = XmlPhysicalPort(1u, "WEIRD", std::nullopt, std::nullopt, std::nullopt, std::nullopt);
    std::string ubpuType = "CPU";
    std::map<LcneKey, XmlNode> xmlNodes;
    xmlNodes[std::make_tuple(1u, 2u, 3u)] = XmlNode(1, 2, 3, ubpuType, nodePorts);

    std::unordered_map<uint32_t, XmlAddressPhysicalPort> addrPorts;
    addrPorts[1u] = XmlAddressPhysicalPort(1u, "c", "b");
    std::map<LcneKey, XmlAddress> xmlAddresses;
    xmlAddresses[std::make_tuple(1u, 2u, 3u)] = XmlAddress(1, 2, 3, "p", addrPorts);

    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(lcne::handler::generateLcnePort(xmlNodes, xmlAddresses, ports), lcne::LCNE_FAIL);

    // 空输入：成功且无输出
    ports.clear();
    EXPECT_EQ(lcne::handler::generateLcnePort({}, {}, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());
}

// ---------------------------------------------------------------------------
// B5-3 追加：lcne_common / lcne_data_handler / lcne_node_collector / lcne_topology
// 覆盖率补齐（只追加，不动上方既有用例）
//
// 1. lcne 的配置与输出路径硬编码为 /etc/witty-ub、/var/witty-ub（普通用户不可写）。
//    通过对自身映像 .rodata 的等长字符串补丁重定向到 /tmp/witty-b5（13 字符等长），
//    使 SaveIpToConfigFile / WriteTopologyToJson 等成功路径可测。
//    补丁在下方用例内首次触发（EnsureHardcodedPathsPatched），先于本块运行的
//    既有用例（如 SaveIpToConfigFileFailsWithoutRoot）不受影响。
// 2. HTTP 依赖由本地 127.0.0.1:34256 的 httplib::Server 模拟 LCNE 设备驱动。
// ---------------------------------------------------------------------------

#include <sys/mman.h>
#include <unistd.h>

#include <charconv>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <sstream>
#include <map>
#include <thread>

#include "httplib.h"

#include "database.h"
#include "http/rack_http_server_handler.h"
#include "lcne_topology.h"

namespace {

struct PatchRegion {
    uintptr_t start;
    uintptr_t end;
    int prot;
};

// /proc/self/maps 权限段中 r/w/x 字符的位置。
constexpr std::size_t PERM_READ_INDEX = 0;
constexpr std::size_t PERM_WRITE_INDEX = 1;
constexpr std::size_t PERM_EXEC_INDEX = 2;

int ParsePerm(const char *perms)
{
    int prot = 0;
    if (perms[PERM_READ_INDEX] == 'r') {
        prot |= PROT_READ;
    }
    if (perms[PERM_WRITE_INDEX] == 'w') {
        prot |= PROT_WRITE;
    }
    if (perms[PERM_EXEC_INDEX] == 'x') {
        prot |= PROT_EXEC;
    }
    return prot;
}

// 单个映射区大小上限（64MB），超出则跳过，避免误扫巨型映射。
constexpr std::size_t MAX_REGION_BYTES = 64u << 20;
// /proc/self/exe 路径缓冲长度。
constexpr std::size_t PATH_BUFFER_SIZE = 4096;

// 扫描 /proc/self/maps，收集本可执行文件自身的可读映射区。
std::vector<PatchRegion> CollectSelfExeRegions(const std::string &exe)
{
    std::vector<PatchRegion> regions;
    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string range, perms, offset, dev, inode, mapPath;
        row >> range >> perms >> offset >> dev >> inode;
        if (!(row >> mapPath)) {
            continue; // 匿名映射无路径
        }
        const auto dash = range.find('-');
        uintptr_t start = 0;
        uintptr_t end = 0;
        const bool rangeOk = dash != std::string::npos &&
                             std::from_chars(range.data(), range.data() + dash, start, 16).ec == std::errc{} &&
                             std::from_chars(range.data() + dash + 1, range.data() + range.size(), end, 16).ec ==
                                 std::errc{};
        if (!rangeOk || mapPath != exe || perms[PERM_READ_INDEX] != 'r' || end <= start ||
            end - start > MAX_REGION_BYTES) {
            continue;
        }
        regions.push_back({start, end, ParsePerm(perms.c_str())});
    }
    return regions;
}

// 把 pos 起长度 len 的区间所在页改为可写（跨页时两页都改）；返回首页是否改写成功。
bool MakePagesWritable(uintptr_t pos, std::size_t len, std::size_t pageSize)
{
    const uintptr_t firstPage = pos & ~(pageSize - 1);
    const uintptr_t lastPage = (pos + len - 1) & ~(pageSize - 1);
    if (mprotect(reinterpret_cast<void *>(firstPage), pageSize, PROT_READ | PROT_WRITE) != 0) {
        return false;
    }
    if (lastPage != firstPage) {
        mprotect(reinterpret_cast<void *>(lastPage), pageSize, PROT_READ | PROT_WRITE);
    }
    return true;
}

// 恢复覆盖 [pos, pos+len) 的所有映射区原始权限。
void RestorePageProtection(uintptr_t pos, std::size_t len, std::size_t pageSize,
                           const std::vector<PatchRegion> &regions)
{
    const uintptr_t firstPage = pos & ~(pageSize - 1);
    const uintptr_t lastPage = (pos + len - 1) & ~(pageSize - 1);
    for (const auto &r : regions) {
        if (firstPage >= r.start && firstPage < r.end) {
            mprotect(reinterpret_cast<void *>(firstPage), pageSize, r.prot);
        }
        if (lastPage != firstPage && lastPage >= r.start && lastPage < r.end) {
            mprotect(reinterpret_cast<void *>(lastPage), pageSize, r.prot);
        }
    }
}

// 在自身可执行映像的只读映射中把 from 原地替换为 to（等长），返回替换次数。
// 逐页按原始权限恢复，避免波及相邻 rw-p（.data）映射。
int PatchHardcodedString(const std::string &from, const std::string &to)
{
    if (from.size() != to.size() || from.empty()) {
        return 0;
    }
    const std::size_t pageSize = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
    char exe[PATH_BUFFER_SIZE] = {0};
    if (readlink("/proc/self/exe", exe, sizeof(exe) - 1) <= 0) {
        return 0;
    }
    const std::vector<PatchRegion> regions = CollectSelfExeRegions(exe);
    int patched = 0;
    for (const auto &region : regions) {
        for (uintptr_t pos = region.start; pos + from.size() <= region.end; ++pos) {
            if (memcmp(reinterpret_cast<void *>(pos), from.data(), from.size()) != 0) {
                continue;
            }
            if (!MakePagesWritable(pos, from.size(), pageSize)) {
                break;
            }
            std::copy(to.begin(), to.end(), reinterpret_cast<char *>(pos));
            RestorePageProtection(pos, from.size(), pageSize, regions);
            ++patched;
            pos += from.size() - 1;
        }
    }
    return patched;
}

// 与 /var/witty-ub、/etc/witty-ub 等长（13 字符）
constexpr const char *K_PATCHED_ROOT = "/tmp/witty-b5";

void EnsureHardcodedPathsPatched()
{
    static bool patched = [] {
        std::filesystem::create_directories(K_PATCHED_ROOT);
        PatchHardcodedString("/var/witty-ub", K_PATCHED_ROOT);
        PatchHardcodedString("/etc/witty-ub", K_PATCHED_ROOT);
        return true;
    }();
    (void)patched;
}

// 本地模拟服务器启动等待：最多轮询轮数与单轮间隔。
constexpr int SERVER_START_ROUNDS = 400;
constexpr int SERVER_POLL_INTERVAL_MS = 5;
// HTTP 状态码（httplib 无符号常量可用，此处按语义命名）。
constexpr int HTTP_OK = 200;
constexpr int HTTP_CREATED = 201;
constexpr int HTTP_NOT_FOUND = 404;
// LCNE 驱动端口（与生产 LCNE_PORT 一致）。
constexpr int LCNE_TEST_PORT = 34256;
// topo-tool 命令行参数个数。
constexpr int TOPO_TOOL_ARGC = 5;

// 本地模拟 LCNE 设备：按请求路径返回可配置的 XML / 状态码
class FakeLcneServer {
public:
    FakeLcneServer()
    {
        namespace c = lcne::common;
        svr_.Get(c::LCNE_NODES_REQ_PATH, [this](const httplib::Request &, httplib::Response &res) {
            Respond(res, c::LCNE_NODES_REQ_PATH);
        });
        svr_.Get(c::LCNE_ADDRESS_REQ_PATH, [this](const httplib::Request &, httplib::Response &res) {
            Respond(res, c::LCNE_ADDRESS_REQ_PATH);
        });
        svr_.Get(c::LCNE_IOU_INFOS_REQ_PATH, [this](const httplib::Request &, httplib::Response &res) {
            Respond(res, c::LCNE_IOU_INFOS_REQ_PATH);
        });
        svr_.Get(c::LCNE_LOGIC_ENTITIES_REQ_PATH, [this](const httplib::Request &, httplib::Response &res) {
            Respond(res, c::LCNE_LOGIC_ENTITIES_REQ_PATH);
        });
        svr_.Post(c::LCNE_NOTIFY_LINK_REQ_PATH, [this](const httplib::Request &, httplib::Response &res) {
            std::lock_guard<std::mutex> lock(mtx_);
            res.status = postStatus_;
            res.set_content("created", "application/yang-data+xml");
        });
    }

    ~FakeLcneServer() { Stop(); }

    void Start()
    {
        thread_ = std::thread([this] { svr_.listen("127.0.0.1", std::stoi(lcne::common::LCNE_PORT)); });
        for (int i = 0; i < SERVER_START_ROUNDS && !svr_.is_running(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(SERVER_POLL_INTERVAL_MS));
        }
    }

    void Stop()
    {
        svr_.stop();
        if (thread_.joinable()) {
            thread_.join();
        }
    }

    bool IsRunning() const { return svr_.is_running(); }

    void SetXml(const char *path, const std::string &xml, int status = HTTP_OK)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        gets_[path] = std::make_pair(status, xml);
    }

    void SetPostStatus(int status)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        postStatus_ = status;
    }

private:
    void Respond(httplib::Response &res, const char *path)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        auto it = gets_.find(path);
        if (it == gets_.end()) {
            res.status = HTTP_NOT_FOUND;
            res.set_content("not found", "text/plain");
            return;
        }
        res.status = it->second.first;
        res.set_content(it->second.second, "application/yang-data+xml");
    }

    httplib::Server svr_;
    std::thread thread_;
    std::mutex mtx_;
    std::map<std::string, std::pair<int, std::string>> gets_;
    int postStatus_ = HTTP_CREATED;
};

// 各 RESTCONF 端点的合法样例
const char *K_LCNE_NODES_XML = R"(<topology>
  <nodes>
    <node>
      <slot>1</slot>
      <ubpu>2</ubpu>
      <iou>3</iou>
      <ubpu-type>CPU</ubpu-type>
      <physical-ports>
        <physical-port>
          <physical-port-id>10</physical-port-id>
          <physical-port-status>UP</physical-port-status>
          <remote-slot>4</remote-slot>
          <remote-ubpu>5</remote-ubpu>
          <remote-iou>6</remote-iou>
          <remote-physical-port-id>11</remote-physical-port-id>
        </physical-port>
      </physical-ports>
    </node>
  </nodes>
</topology>)";

const char *K_LCNE_IOU_XML = R"(<vbussw-service>
  <iou-infos>
    <iou-info>
      <guid>guid-1</guid>
      <bus-controller-eid>eid-1</bus-controller-eid>
      <slot-id>1</slot-id>
      <ubpu-id>2</ubpu-id>
      <iou-id>3</iou-id>
      <primary-cna>cna-1</primary-cna>
      <iou-status>normal</iou-status>
    </iou-info>
  </iou-infos>
</vbussw-service>)";

const char *K_LCNE_ADDRESS_XML = R"(<topology>
  <addresses>
    <address>
      <slot>1</slot>
      <ubpu>2</ubpu>
      <iou>3</iou>
      <bus-primary-cna>primary-cna</bus-primary-cna>
      <physical-ports>
        <physical-port>
          <physical-port-id>10</physical-port-id>
          <port-cna>port-cna</port-cna>
          <bus-port-cna>bus-cna</bus-port-cna>
        </physical-port>
      </physical-ports>
    </address>
  </addresses>
</topology>)";

const char *K_LCNE_LOGIC_XML = R"(<inventory>
  <logic-entities>
    <logic-entity>
      <state>online</state>
    </logic-entity>
  </logic-entities>
</inventory>)";

} // namespace

class LcneServerTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        EnsureHardcodedPathsPatched();
        server_ = std::make_unique<FakeLcneServer>();
        server_->Start();
        ASSERT_TRUE(server_->IsRunning());
    }

    void TearDown() override
    {
        server_->Stop();
        server_.reset();
    }

    std::unique_ptr<FakeLcneServer> server_;
};

// ---------------------------------------------------------------------------
// B5-3 追加：lcne_common 其余分支
// ---------------------------------------------------------------------------

TEST_F(LcneServerTest, GetHttpDataSucceedsWithServer)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    std::string body;
    EXPECT_EQ(lcne::common::GetHttpData(body, lcne::common::LCNE_NODES_REQ_PATH), lcne::LCNE_SUCCESS);
    EXPECT_EQ(body, K_LCNE_NODES_XML);
}

TEST_F(LcneServerTest, GetHttpDataFailsOnEmptyBody)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, "");
    std::string body;
    EXPECT_EQ(lcne::common::GetHttpData(body, lcne::common::LCNE_NODES_REQ_PATH), lcne::LCNE_FAIL);
}

TEST_F(LcneServerTest, PostLinkInfoNotifyStatusBranches)
{
    // 201：订阅成功
    server_->SetPostStatus(HTTP_CREATED);
    EXPECT_EQ(lcne::common::PostLinkInfoNotify(), lcne::LCNE_SUCCESS);
    // 412：重复订阅，仍按成功处理
    server_->SetPostStatus(412);
    EXPECT_EQ(lcne::common::PostLinkInfoNotify(), lcne::LCNE_SUCCESS);
    // 其他状态码：失败
    server_->SetPostStatus(500);
    EXPECT_EQ(lcne::common::PostLinkInfoNotify(), lcne::LCNE_FAIL);
}

TEST(LcneCommon, CheckXMLRejectsEmptyCdataText)
{
    // CDATA 文本节点存在但内容为空：GetText() 返回 ""，命中 strlen==0 分支
    EXPECT_EQ(lcne::common::checkXML(ParseRoot("<a><![CDATA[]]></a>")), lcne::LCNE_FAIL);
}

TEST(LcneCommon, MkdirRecursiveFailsWhenParentCreationFails)
{
    // 深层目标：父目录 /ro/a 不可创建，递归失败沿调用链上抛
    TempDir dir;
    std::string ro = (dir.Path() / "ro").string();
    ASSERT_TRUE(std::filesystem::create_directory(ro));
    ASSERT_EQ(::chmod(ro.c_str(), 0555), 0);
    EXPECT_FALSE(lcne::common::MkdirRecursive(ro + "/a/b"));
    ::chmod(ro.c_str(), 0755);
}

TEST(LcneCommon, SaveIpToConfigFileSucceedsAfterPatch)
{
    EnsureHardcodedPathsPatched();
    std::string configPath = std::string(K_PATCHED_ROOT) + "/config.xml";

    // 文件不存在：创建声明、根元素并新建 ip 子元素
    std::filesystem::remove(configPath);
    EXPECT_EQ(lcne::common::SaveIpToConfigFile("10.0.0.1"), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(std::filesystem::exists(configPath));

    // 存在带 ip 的合法文件：更新既有 ip 文本
    {
        std::ofstream out(configPath);
        out << "<root><ip>0.0.0.0</ip></root>";
    }
    EXPECT_EQ(lcne::common::SaveIpToConfigFile("10.0.0.2"), lcne::LCNE_SUCCESS);
    {
        std::ifstream in(configPath);
        std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        EXPECT_EQ(content.find("0.0.0.0"), std::string::npos);
        EXPECT_NE(content.find("10.0.0.2"), std::string::npos);
    }

    // 存在无 ip 的合法文件：新建 ip 子元素
    {
        std::ofstream out(configPath);
        out << "<root></root>";
    }
    EXPECT_EQ(lcne::common::SaveIpToConfigFile("10.0.0.3"), lcne::LCNE_SUCCESS);
    {
        std::ifstream in(configPath);
        std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        EXPECT_NE(content.find("10.0.0.3"), std::string::npos);
    }
}

TEST(LcneCommon, SaveIpToConfigFileFailsOnCorruptConfig)
{
    EnsureHardcodedPathsPatched();
    std::string configPath = std::string(K_PATCHED_ROOT) + "/config.xml";
    {
        std::ofstream out(configPath);
        out << "not-an-xml";
    }
    EXPECT_EQ(lcne::common::SaveIpToConfigFile("10.0.0.4"), lcne::LCNE_FAIL);
}

// ---------------------------------------------------------------------------
// B5-3 追加：lcne_data_handler 的 HTTP + XML 解析路径
// ---------------------------------------------------------------------------

TEST_F(LcneServerTest, GetXMLNodesParsesServerResponse)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    std::map<lcne::handler::LcneKey, lcne::handler::XmlNode> nodes;
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    ASSERT_EQ(nodes.size(), 1u);
    const auto &node = nodes.at(std::make_tuple(1u, 2u, 3u));
    EXPECT_EQ(node.ubpuType, "CPU");
    ASSERT_EQ(node.physicalPorts.size(), 1u);
    EXPECT_EQ(node.physicalPorts.at(10u).physicalPortStatus, "UP");
    ASSERT_TRUE(node.physicalPorts.at(10u).remoteSlot.has_value());
    EXPECT_EQ(*node.physicalPorts.at(10u).remoteSlot, 4u);
}

TEST_F(LcneServerTest, GetXMLNodesBadResponsesStillReportSuccess)
{
    // 生产问题（勿修）：getXMLNodes 中局部 ret 被 GetHttpData 的成功结果覆盖，
    // HTTP 成功后的所有解析失败分支 return ret 实际返回 LCNE_SUCCESS。
    // 此处按当前真实行为断言，并校验副作用（输出 map 为空）。
    std::map<lcne::handler::LcneKey, lcne::handler::XmlNode> nodes;
    // 坏 XML
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, "<topology><unclosed></topology>");
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    // 缺 nodes 子元素
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, "<topology/>");
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    // node 的 slot 非数字（元素存在但文本非法，stoul 抛 invalid_argument）
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH,
                    "<topology><nodes><node><slot>x</slot><ubpu>2</ubpu><iou>3</iou><ubpu-type>CPU</ubpu-type>"
                    "<physical-ports/></node></nodes></topology>");
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    // node 的 ubpu-type 无文本
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH,
                    "<topology><nodes><node><slot>1</slot><ubpu>2</ubpu><iou>3</iou><ubpu-type/>"
                    "<physical-ports/></node></nodes></topology>");
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    // 空物理端口容器：成功且端口为空
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH,
                    "<topology><nodes><node><slot>1</slot><ubpu>2</ubpu><iou>3</iou><ubpu-type>NPU</ubpu-type>"
                    "<physical-ports/></node></nodes></topology>");
    nodes.clear();
    EXPECT_EQ(lcne::handler::getXMLNodes(lcne::common::LCNE_NODES_REQ_PATH, nodes), lcne::LCNE_SUCCESS);
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_TRUE(nodes.begin()->second.physicalPorts.empty());
}

TEST_F(LcneServerTest, GetXMLIouInfoParsesServerResponse)
{
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    std::map<lcne::handler::LcneKey, lcne::handler::XmlIouInfo> ious;
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ious.size(), 1u);
    const auto &iou = ious.at(std::make_tuple(1u, 2u, 3u));
    EXPECT_EQ(iou.guid, "guid-1");
    EXPECT_EQ(iou.busControllerEid, "eid-1");
    EXPECT_EQ(iou.primaryCna, "cna-1");
    EXPECT_EQ(iou.iouStatus, "normal");
}

TEST_F(LcneServerTest, GetXMLIouInfoBadResponsesStillReportSuccess)
{
    // 生产问题（勿修）：与 getXMLNodes 相同，getXMLIouInfo 的解析失败分支返回 LCNE_SUCCESS
    std::map<lcne::handler::LcneKey, lcne::handler::XmlIouInfo> ious;
    // 坏 XML
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, "<unclosed>");
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ious.empty());
    // 缺 iou-infos 子元素
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, "<root/>");
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ious.empty());
    // 缺 guid 子元素（checkXML(null) 安全失败）
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH,
                    "<root><iou-infos><iou-info><bus-controller-eid>e</bus-controller-eid><slot-id>1</slot-id>"
                    "<ubpu-id>2</ubpu-id><iou-id>3</iou-id><primary-cna>c</primary-cna><iou-status>normal</iou-status>"
                    "</iou-info></iou-infos></root>");
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ious.empty());
    // slot-id 非数字
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH,
                    "<root><iou-infos><iou-info><guid>g</guid><bus-controller-eid>e</bus-controller-eid>"
                    "<slot-id>y</slot-id><ubpu-id>2</ubpu-id><iou-id>3</iou-id><primary-cna>c</primary-cna>"
                    "<iou-status>normal</iou-status></iou-info></iou-infos></root>");
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ious.empty());
    // iou-status 无文本
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH,
                    "<root><iou-infos><iou-info><guid>g</guid><bus-controller-eid>e</bus-controller-eid>"
                    "<slot-id>1</slot-id><ubpu-id>2</ubpu-id><iou-id>3</iou-id><primary-cna>c</primary-cna>"
                    "<iou-status/></iou-info></iou-infos></root>");
    EXPECT_EQ(lcne::handler::getXMLIouInfo(lcne::common::LCNE_IOU_INFOS_REQ_PATH, ious), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ious.empty());
}

TEST_F(LcneServerTest, GetXMLAddressParsesServerResponse)
{
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, K_LCNE_ADDRESS_XML);
    std::map<lcne::handler::LcneKey, lcne::handler::XmlAddress> addresses;
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    ASSERT_EQ(addresses.size(), 1u);
    const auto &addr = addresses.at(std::make_tuple(1u, 2u, 3u));
    EXPECT_EQ(addr.primaryCna, "primary-cna");
    ASSERT_EQ(addr.physicalPorts.size(), 1u);
    EXPECT_EQ(addr.physicalPorts.at(10u).portCna, "port-cna");
    EXPECT_EQ(addr.physicalPorts.at(10u).busPortCna, "bus-cna");
}

TEST_F(LcneServerTest, GetXMLAddressBadResponsesStillReportSuccess)
{
    // 生产问题（勿修）：与 getXMLNodes 相同，getXMLAddress 的解析失败分支返回 LCNE_SUCCESS
    std::map<lcne::handler::LcneKey, lcne::handler::XmlAddress> addresses;
    // 坏 XML
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, "<unclosed>");
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(addresses.empty());
    // 缺 addresses 子元素
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, "<root/>");
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(addresses.empty());
    // slot 非数字（注意 address 必须带 bus-primary-cna，否则实现会解引用空指针——生产缺陷，避免触发）
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH,
                    "<root><addresses><address><slot>z</slot><ubpu>2</ubpu><iou>3</iou>"
                    "<bus-primary-cna>p</bus-primary-cna><physical-ports/></address></addresses></root>");
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(addresses.empty());
    // 物理端口 id 非数字
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH,
                    "<root><addresses><address><slot>1</slot><ubpu>2</ubpu><iou>3</iou>"
                    "<bus-primary-cna>p</bus-primary-cna><physical-ports><physical-port><physical-port-id>q"
                    "</physical-port-id><port-cna>a</port-cna><bus-port-cna>b</bus-port-cna></physical-port>"
                    "</physical-ports></address></addresses></root>");
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(addresses.empty());
    // 空物理端口容器：成功
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH,
                    "<root><addresses><address><slot>1</slot><ubpu>2</ubpu><iou>3</iou>"
                    "<bus-primary-cna>p</bus-primary-cna><physical-ports/></address></addresses></root>");
    addresses.clear();
    EXPECT_EQ(lcne::handler::getXMLAddress(lcne::common::LCNE_ADDRESS_REQ_PATH, addresses), lcne::LCNE_SUCCESS);
    ASSERT_EQ(addresses.size(), 1u);
    EXPECT_TRUE(addresses.begin()->second.physicalPorts.empty());
}

TEST_F(LcneServerTest, GetXmlLogicEntitiesParsesServerResponse)
{
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
    std::shared_ptr<lcne::handler::XmlLogicEntity> entity;
    EXPECT_EQ(lcne::handler::GetXmlLogicEntities(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, entity),
             lcne::LCNE_SUCCESS);
    ASSERT_NE(entity, nullptr);
    EXPECT_EQ(entity->state, "online");
}

TEST_F(LcneServerTest, GetXmlLogicEntitiesBadResponsesStillReportSuccess)
{
    // 生产问题（勿修）：与 getXMLNodes 相同，GetXmlLogicEntities 的解析失败分支返回 LCNE_SUCCESS
    std::shared_ptr<lcne::handler::XmlLogicEntity> entity;
    // 坏 XML
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, "<unclosed>");
    EXPECT_EQ(lcne::handler::GetXmlLogicEntities(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, entity),
             lcne::LCNE_SUCCESS);
    EXPECT_EQ(entity, nullptr);
    // 缺 logic-entity 子元素（实现中 logic-entities 缺失会对空指针链式调用，避免触发）
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, "<root><logic-entities/></root>");
    EXPECT_EQ(lcne::handler::GetXmlLogicEntities(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, entity),
             lcne::LCNE_SUCCESS);
    EXPECT_EQ(entity, nullptr);
    // state 元素无文本
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH,
                     "<root><logic-entities><logic-entity><state/></logic-entity></logic-entities></root>");
    EXPECT_EQ(lcne::handler::GetXmlLogicEntities(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, entity),
             lcne::LCNE_SUCCESS);
    EXPECT_EQ(entity, nullptr);
}

// ---------------------------------------------------------------------------
// B5-3 追加：lcne_node_collector
// ---------------------------------------------------------------------------

TEST_F(LcneServerTest, LcneNodeCollectorDeviceDataMap)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    EXPECT_EQ(collector.GetCurrNodeDeviceDataMap(nodes), lcne::LCNE_SUCCESS);
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0]->deviceId, 1u);
    EXPECT_EQ(nodes[0]->chipNum, 2u);
    EXPECT_EQ(nodes[0]->dieNum, 3u);
    EXPECT_EQ(nodes[0]->chipType, topology::node::ChipType::CPU);
}

TEST_F(LcneServerTest, LcneNodeCollectorUbCDataMap)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ubcs.size(), 1u);
    EXPECT_EQ(ubcs[0]->dieGuid, "guid-1");
    EXPECT_EQ(ubcs[0]->primaryCna, "cna-1");
    EXPECT_EQ(ubcs[0]->dieState, topology::node::DieState::NORMAL);
    EXPECT_EQ(ubcs[0]->ubcState, topology::node::UbCState::ONLINE);
}

TEST_F(LcneServerTest, LcneNodeCollectorPortDataMap)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, K_LCNE_ADDRESS_XML);
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(collector.GetCurrNodePortDataMap(ports), lcne::LCNE_SUCCESS);
    ASSERT_EQ(ports.size(), 1u);
    EXPECT_EQ(ports[0]->portId, 10u);
    EXPECT_EQ(ports[0]->portCna, "port-cna");
    EXPECT_EQ(ports[0]->primaryCna, "primary-cna");
    EXPECT_EQ(ports[0]->portState, topology::node::PortState::UP);
    ASSERT_TRUE(ports[0]->remoteSlotId.has_value());
    EXPECT_EQ(*ports[0]->remoteSlotId, 4u);
    ASSERT_TRUE(ports[0]->remoteIouId.has_value());
    EXPECT_EQ(*ports[0]->remoteIouId, 6u);
}

TEST_F(LcneServerTest, LcneNodeCollectorAllDataMap)
{
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, K_LCNE_ADDRESS_XML);
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(collector.GetCurrNodeAllDataMap(nodes, ubcs, ports), lcne::LCNE_SUCCESS);
    EXPECT_EQ(nodes.size(), 1u);
    EXPECT_EQ(ubcs.size(), 1u);
    EXPECT_EQ(ports.size(), 1u);
}

TEST_F(LcneServerTest, LcneNodeCollectorDataMapsIgnoreBadNodesXml)
{
    // 生产问题（勿修）：getXMLNodes 的失败分支返回 LCNE_SUCCESS（ret 被 GetHttpData 覆盖），
    // 坏 nodes XML 不会使采集方法失败，仅得到空数据
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, "<unclosed>");
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(collector.GetCurrNodeDeviceDataMap(nodes), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ubcs.empty());
    EXPECT_EQ(collector.GetCurrNodePortDataMap(ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(ports.empty());
    EXPECT_EQ(collector.GetCurrNodeAllDataMap(nodes, ubcs, ports), lcne::LCNE_SUCCESS);
}

TEST(LcneNodeCollector, DataMapsFailWithoutServer)
{
    // 34256 无监听：全部 HTTP 入口失败
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(collector.GetCurrNodeDeviceDataMap(nodes), lcne::LCNE_FAIL);
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_FAIL);
    EXPECT_EQ(collector.GetCurrNodePortDataMap(ports), lcne::LCNE_FAIL);
    EXPECT_EQ(collector.GetCurrNodeAllDataMap(nodes, ubcs, ports), lcne::LCNE_FAIL);
}

TEST_F(LcneServerTest, LcneNodeCollectorDataMapsFailOnEmptyBodiesAndBadStates)
{
    lcne::collector::LcneNodeCollector collector;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;

    // nodes 有效但 iou 响应体为空：GetHttpData 失败 → UbCDataMap 失败
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, "");
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_FAIL);

    // nodes/iou 有效但 logic 响应体为空 → 失败
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, "");
    ubcs.clear();
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_FAIL);

    // iou-status 无法映射 die 状态：generateLcneUBController 失败
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH,
                    "<root><iou-infos><iou-info><guid>g</guid><bus-controller-eid>e</bus-controller-eid>"
                    "<slot-id>1</slot-id><ubpu-id>2</ubpu-id><iou-id>3</iou-id><primary-cna>c</primary-cna>"
                    "<iou-status>weird</iou-status></iou-info></iou-infos></root>");
    server_->SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
    ubcs.clear();
    EXPECT_EQ(collector.GetCurrNodeUbCDataMap(ubcs), lcne::LCNE_FAIL);

    // nodes 有效但 address 响应体为空：PortDataMap 失败
    server_->SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, "");
    EXPECT_EQ(collector.GetCurrNodePortDataMap(ports), lcne::LCNE_FAIL);

    // 物理端口状态无法映射：generateLcnePort 失败
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH,
                    "<topology><nodes><node><slot>1</slot><ubpu>2</ubpu><iou>3</iou><ubpu-type>CPU</ubpu-type>"
                    "<physical-ports><physical-port><physical-port-id>10</physical-port-id>"
                    "<physical-port-status>WEIRD</physical-port-status><remote-slot>4</remote-slot>"
                    "<remote-ubpu>5</remote-ubpu><remote-iou>6</remote-iou>"
                    "<remote-physical-port-id>11</remote-physical-port-id></physical-port>"
                    "</physical-ports></node></nodes></topology>");
    server_->SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, K_LCNE_ADDRESS_XML);
    ports.clear();
    EXPECT_EQ(collector.GetCurrNodePortDataMap(ports), lcne::LCNE_FAIL);
}

// ---------------------------------------------------------------------------
// B5-3 追加：lcne_topology
// ---------------------------------------------------------------------------

namespace {

// 注册 NodeLocalCollectorModule（注入 Database）与 JSONModule 到 UbseContext，
// 使 LcneTopology 构造函数能取到有效模块
std::shared_ptr<topology::node::NodeLocalCollectorModule> SetupLcneTopologyModules(const std::string &dbPath,
                                                                                   bool createTables)
{
    auto &context = ubse::context::UbseContext::GetInstance();
    auto nodeLocal = std::make_shared<topology::node::NodeLocalCollectorModule>();
    nodeLocal->Initialize();
    auto db = std::make_shared<database::Database>();
    EXPECT_EQ(db->OpenDb(dbPath, true), database::OP_RET::SUCCESS);
    nodeLocal->GetCollector()->InitDb(db);
    if (createTables) {
        nodeLocal->GetCollector()->StartDb();
    }
    context.InitModule<topology::node::NodeLocalCollectorModule>(nodeLocal);
    auto jsonModule = std::make_shared<witty_json::module::JSONModule>();
    jsonModule->Initialize();
    context.InitModule<witty_json::module::JSONModule>(jsonModule);
    return nodeLocal;
}

void ServeAllLcneXml(FakeLcneServer &server)
{
    server.SetXml(lcne::common::LCNE_NODES_REQ_PATH, K_LCNE_NODES_XML);
    server.SetXml(lcne::common::LCNE_IOU_INFOS_REQ_PATH, K_LCNE_IOU_XML);
    server.SetXml(lcne::common::LCNE_ADDRESS_REQ_PATH, K_LCNE_ADDRESS_XML);
    server.SetXml(lcne::common::LCNE_LOGIC_ENTITIES_REQ_PATH, K_LCNE_LOGIC_XML);
}

} // namespace

TEST_F(LcneServerTest, LcneTopologyCreateTopolgyWritesJson)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    ServeAllLcneXml(*server_);

    const std::string outputPath = std::string(K_PATCHED_ROOT) + "/lcne-topology.json";
    std::filesystem::remove(outputPath);

    lcne::topo::LcneTopology topo;
    EXPECT_EQ(topo.CreateTopolgy(), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(std::filesystem::exists(outputPath));
}

TEST_F(LcneServerTest, LcneTopologyCreateTopolgyClosModeClearsRemoteFields)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    ServeAllLcneXml(*server_);

    // networkMode=clos：端口 remote 字段被清空
    char arg0[] = "topo-tool";
    char arg1[] = "--network-mode";
    char arg2[] = "clos";
    char arg3[] = "--pod-mode";
    char arg4[] = "off";
    char *argv[] = {arg0, arg1, arg2, arg3, arg4};
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().ParseTopoToolsArgs(TOPO_TOOL_ARGC, argv), RACK_OK);
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().GetTopoToolsArgs().networkMode, "clos");

    lcne::topo::LcneTopology topo;
    EXPECT_EQ(topo.CreateTopolgy(), lcne::LCNE_SUCCESS);

    // 恢复 fullmesh，避免影响后续用例
    char mode[] = "fullmesh";
    char *argv2[] = {arg0, arg1, mode, arg3, arg4};
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().ParseTopoToolsArgs(TOPO_TOOL_ARGC, argv2), RACK_OK);
}

TEST_F(LcneServerTest, LcneTopologyCreateTopolgyFailsWithoutServer)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    // 坏 XML 因生产缺陷（getXML* 失败分支误报成功）无法触发失败路径；
    // 直接关闭模拟设备使 HTTP 请求连接失败，GetCurrNodeAllDataMap 返回失败
    server_->Stop();

    lcne::topo::LcneTopology topo;
    EXPECT_EQ(topo.CreateTopolgy(), lcne::LCNE_FAIL);
}

TEST_F(LcneServerTest, LcneTopologyCreateTopolgyIgnoresEarlierFailures)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    ServeAllLcneXml(*server_);
    // 生产问题（勿修）：GetCurrNodeAllDataMap 前两个调用的返回值被覆盖，
    // nodes XML 坏但地址 XML 有效时整体仍报成功
    server_->SetXml(lcne::common::LCNE_NODES_REQ_PATH, "<unclosed>");

    lcne::topo::LcneTopology topo;
    EXPECT_EQ(topo.CreateTopolgy(), lcne::LCNE_SUCCESS);
}

TEST_F(LcneServerTest, LcneTopologyGetTopologiesFromDb)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    lcne::topo::LcneTopology topo;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(topo.GetCurTopolgy(nodes, ubcs, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
    EXPECT_TRUE(ubcs.empty());
    EXPECT_TRUE(ports.empty());
    EXPECT_EQ(topo.GetHisTopolgy(nodes, ubcs, ports), lcne::LCNE_SUCCESS);
    EXPECT_TRUE(nodes.empty());
}

TEST_F(LcneServerTest, LcneTopologyGetTopologiesFailWithoutTables)
{
    TempDir dir;
    // 只 InitDb 不 StartDb：表不存在，查询失败
    SetupLcneTopologyModules((dir.Path() / "notables.db").string(), false);
    lcne::topo::LcneTopology topo;
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(topo.GetCurTopolgy(nodes, ubcs, ports), lcne::LCNE_FAIL);
    EXPECT_EQ(topo.GetHisTopolgy(nodes, ubcs, ports), lcne::LCNE_FAIL);
}

TEST_F(LcneServerTest, LcneTopologyRegLinkNotifyHandlerAndSubChanges)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    ServeAllLcneXml(*server_);
    server_->SetPostStatus(HTTP_CREATED);

    lcne::topo::LcneTopology topo;
    EXPECT_EQ(topo.RegLinkNotifyHttpHandler(), lcne::LCNE_SUCCESS);

    // 注册的路由经 Dispatch 触发 LinkNotifyHandlerFunc（内部 CreateTopolgy 成功）→ 200
    rack::com::RackComContext comCtx;
    rack::com::RackHttpRequest req;
    req.method = rack::com::RackHttpMethod::POST;
    req.path = lcne::common::LCNE_NOTIFY_TOPO_PATH;
    auto res = rack::com::RackHttpServerHandler::GetInstance().Dispatch(comCtx, req);
    ASSERT_TRUE(res.Ok());
    EXPECT_EQ(res.value->status, rack::com::OK_200);

    // 订阅链路变化：201 → 成功
    EXPECT_EQ(topo.SubTopolgyChanges(), lcne::LCNE_SUCCESS);
    // 412：重复订阅仍成功
    server_->SetPostStatus(412);
    EXPECT_EQ(topo.SubTopolgyChanges(), lcne::LCNE_SUCCESS);
    // 500：失败
    server_->SetPostStatus(500);
    EXPECT_EQ(topo.SubTopolgyChanges(), lcne::LCNE_FAIL);
}

TEST_F(LcneServerTest, LcneTopologyInitHandlerFuncStatusBranches)
{
    TempDir dir;
    SetupLcneTopologyModules((dir.Path() / "topo.db").string(), true);
    ServeAllLcneXml(*server_);

    // 保证 SaveIpToConfigFile 走成功路径
    std::string configPath = std::string(K_PATCHED_ROOT) + "/config.xml";
    {
        std::ofstream out(configPath);
        out << "<root/>";
    }

    lcne::topo::LcneTopology topo;
    rack::com::RackComContext comCtx;
    rack::com::RackHttpRequest req;
    req.remote_addr = "127.0.0.1";
    req.remote_port = LCNE_TEST_PORT;

    // SaveIp 成功 + GetCurTopolgy 成功 → 200
    auto res = topo.GetLcneTopologyInitHandlerFunc(comCtx, req);
    ASSERT_TRUE(res.Ok());
    EXPECT_EQ(res.value->status, rack::com::OK_200);

    // SaveIp 失败（坏配置文件）→ 404
    {
        std::ofstream out(configPath);
        out << "corrupt";
    }
    res = topo.GetLcneTopologyInitHandlerFunc(comCtx, req);
    ASSERT_TRUE(res.Ok());
    EXPECT_EQ(res.value->status, rack::com::NotFound_404);

    // GetLcneTopologyHandlerFunc 恒 200
    auto plain = topo.GetLcneTopologyHandlerFunc(comCtx, req);
    ASSERT_TRUE(plain.Ok());
    EXPECT_EQ(plain.value->status, rack::com::OK_200);
}

TEST_F(LcneServerTest, LcneTopologyInitHandlerReturns404WhenQueryFails)
{
    TempDir dir;
    // 无表库：SaveIp 成功但查询失败 → 404
    SetupLcneTopologyModules((dir.Path() / "notables.db").string(), false);
    ServeAllLcneXml(*server_);

    std::string configPath = std::string(K_PATCHED_ROOT) + "/config.xml";
    {
        std::ofstream out(configPath);
        out << "<root/>";
    }

    lcne::topo::LcneTopology topo;
    rack::com::RackComContext comCtx;
    rack::com::RackHttpRequest req;
    req.remote_addr = "127.0.0.1";
    req.remote_port = LCNE_TEST_PORT;
    auto res = topo.GetLcneTopologyInitHandlerFunc(comCtx, req);
    ASSERT_TRUE(res.Ok());
    EXPECT_EQ(res.value->status, rack::com::NotFound_404);
}
