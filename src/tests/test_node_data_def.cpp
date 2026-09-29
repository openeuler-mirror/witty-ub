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

#include <string>
#include <vector>

#include "node_data_def.h"

TEST(Str2ChipType, KnownTypes) {
    EXPECT_EQ(topology::node::Str2ChipType("CPU"), topology::node::ChipType::CPU);
    EXPECT_EQ(topology::node::Str2ChipType("CPU-LINK"), topology::node::ChipType::CPULINK);
    EXPECT_EQ(topology::node::Str2ChipType("NPU"), topology::node::ChipType::NPU);
}

TEST(Str2ChipType, UnknownType) {
    EXPECT_EQ(topology::node::Str2ChipType("UNKNOWN"), topology::node::ChipType::UNKNOWN);
    EXPECT_EQ(topology::node::Str2ChipType("GARBAGE"), topology::node::ChipType::UNKNOWN);
}

TEST(ChipType2Str, AllTypes) {
    EXPECT_EQ(topology::node::ChipType2Str(topology::node::ChipType::CPU), "CPU");
    EXPECT_EQ(topology::node::ChipType2Str(topology::node::ChipType::CPULINK), "CPU-LINK");
    EXPECT_EQ(topology::node::ChipType2Str(topology::node::ChipType::NPU), "NPU");
    EXPECT_EQ(topology::node::ChipType2Str(topology::node::ChipType::UNKNOWN), "UNKNOWN");
}

TEST(Str2DieState, KnownStates) {
    EXPECT_EQ(topology::node::Str2DieState("NORMAL"), topology::node::DieState::NORMAL);
    EXPECT_EQ(topology::node::Str2DieState("ABNORMAL"), topology::node::DieState::ABNORMAL);
    EXPECT_EQ(topology::node::Str2DieState("UNKNOWN"), topology::node::DieState::UNKNOWN);
}

TEST(Str2DieState, UnknownState) {
    EXPECT_EQ(topology::node::Str2DieState("GARBAGE"), topology::node::DieState::UNKNOWN);
}

TEST(Str2UbCState, KnownStates) {
    EXPECT_EQ(topology::node::Str2UbCState("INITIAL"), topology::node::UbCState::INITIAL);
    EXPECT_EQ(topology::node::Str2UbCState("ONLINE"), topology::node::UbCState::ONLINE);
    EXPECT_EQ(topology::node::Str2UbCState("OFFLINE"), topology::node::UbCState::OFFLINE);
    EXPECT_EQ(topology::node::Str2UbCState("RESETTING"), topology::node::UbCState::RESETTING);
    EXPECT_EQ(topology::node::Str2UbCState("ABNORMAL"), topology::node::UbCState::ABNORMAL);
}

TEST(Str2UbCState, UnknownState) {
    EXPECT_EQ(topology::node::Str2UbCState("GARBAGE"), topology::node::UbCState::UNKNOWN);
}

TEST(UbcState2Str, AllStates) {
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::INITIAL), "INITIAL");
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::ONLINE), "ONLINE");
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::OFFLINE), "OFFLINE");
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::RESETTING), "RESETTING");
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::ABNORMAL), "ABNORMAL");
    EXPECT_EQ(topology::node::UbcState2Str(topology::node::UbCState::UNKNOWN), "UNKNOWN");
}

TEST(DieState2Str, AllStates) {
    EXPECT_EQ(topology::node::DieState2Str(topology::node::DieState::NORMAL), "NORMAL");
    EXPECT_EQ(topology::node::DieState2Str(topology::node::DieState::ABNORMAL), "ABNORMAL");
    EXPECT_EQ(topology::node::DieState2Str(topology::node::DieState::UNKNOWN), "UNKNOWN");
}

TEST(Str2PortState, KnownStates) {
    EXPECT_EQ(topology::node::Str2PortState("UP"), topology::node::PortState::UP);
    EXPECT_EQ(topology::node::Str2PortState("DOWN"), topology::node::PortState::DOWN);
    EXPECT_EQ(topology::node::Str2PortState("UNKNOWN"), topology::node::PortState::UNKNOWN);
}

TEST(Str2PortState, UnknownState) {
    EXPECT_EQ(topology::node::Str2PortState("GARBAGE"), topology::node::PortState::UNKNOWN);
}

TEST(PortState2Str, AllStates) {
    EXPECT_EQ(topology::node::PortState2Str(topology::node::PortState::UP), "UP");
    EXPECT_EQ(topology::node::PortState2Str(topology::node::PortState::DOWN), "DOWN");
    EXPECT_EQ(topology::node::PortState2Str(topology::node::PortState::UNKNOWN), "UNKNOWN");
}

TEST(GetHostIps, SingleIp) {
    auto result = topology::node::GetHostIps("192.168.1.1");
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0], "192.168.1.1");
}

TEST(GetHostIps, MultipleIps) {
    auto result = topology::node::GetHostIps("192.168.1.1:192.168.1.2");
    ASSERT_EQ(result.size(), 2u);
    EXPECT_EQ(result[0], "192.168.1.1");
    EXPECT_EQ(result[1], "192.168.1.2");
}

TEST(GetPortIds, SinglePort) {
    auto result = topology::node::GetPortIds("8080");
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0], 8080u);
}

TEST(GetPortIds, MultiplePorts) {
    auto result = topology::node::GetPortIds("8080:9090");
    ASSERT_EQ(result.size(), 2u);
    EXPECT_EQ(result[0], 8080u);
    EXPECT_EQ(result[1], 9090u);
}

TEST(MergeStr, SingleElement) {
    std::vector<std::string> v = {"hello"};
    EXPECT_EQ(topology::node::MergeStr(v), "hello");
}

TEST(MergeStr, MultipleElements) {
    std::vector<std::string> v = {"a", "b", "c"};
    EXPECT_EQ(topology::node::MergeStr(v), "a,b,c");
}

TEST(MergeStr, Empty) {
    std::vector<std::string> v;
    EXPECT_EQ(topology::node::MergeStr(v), "");
}

TEST(DataMapToObj, NodeFromMap) {
    std::unordered_map<std::string, std::string> map;
    map["deviceId"] = "1";
    map["slotId"] = "2";
    map["hostname"] = "host1";
    map["ipAddrs"] = "10.0.0.1";
    map["chipNum"] = "4";
    map["dieNum"] = "8";
    map["chipType"] = "CPU";
    topology::node::Node obj;
    topology::node::DataMapToObj(map, obj);
    EXPECT_EQ(obj.deviceId, 1u);
    EXPECT_EQ(obj.slotId, 2u);
    EXPECT_EQ(obj.hostname, "host1");
    ASSERT_EQ(obj.ipAddrs.size(), 1u);
    EXPECT_EQ(obj.ipAddrs[0], "10.0.0.1");
    EXPECT_EQ(obj.chipNum, 4u);
    EXPECT_EQ(obj.dieNum, 8u);
    EXPECT_EQ(obj.chipType, topology::node::ChipType::CPU);
}

TEST(DataMapToObj, UbControllerFromMap) {
    std::unordered_map<std::string, std::string> map;
    map["dieGuid"] = "guid-1";
    map["ubcEid"] = "eid-1";
    map["deviceId"] = "10";
    map["slotId"] = "2";
    map["chipId"] = "3";
    map["dieId"] = "4";
    map["primaryCna"] = "cna-1";
    map["portIds"] = "100:200";
    map["dieState"] = "NORMAL";
    map["ubcState"] = "ONLINE";
    topology::node::UbController obj;
    topology::node::DataMapToObj(map, obj);
    EXPECT_EQ(obj.dieGuid, "guid-1");
    EXPECT_EQ(obj.ubcEid, "eid-1");
    EXPECT_EQ(obj.deviceId, 10u);
    EXPECT_EQ(obj.slotId, 2u);
    EXPECT_EQ(obj.chipId, 3u);
    EXPECT_EQ(obj.dieId, 4u);
    EXPECT_EQ(obj.primaryCna, "cna-1");
    ASSERT_EQ(obj.portIds.size(), 2u);
    EXPECT_EQ(obj.portIds[0], 100u);
    EXPECT_EQ(obj.portIds[1], 200u);
    EXPECT_EQ(obj.dieState, topology::node::DieState::NORMAL);
    EXPECT_EQ(obj.ubcState, topology::node::UbCState::ONLINE);
}

TEST(DataMapToObj, PortFromMap) {
    std::unordered_map<std::string, std::string> map;
    map["portId"] = "7";
    map["portCna"] = "pcna";
    map["primaryCna"] = "cna";
    map["deviceId"] = "11";
    map["portState"] = "UP";
    map["remotePortIds"] = "8";
    map["remoteDeviceId"] = "12";
    map["remoteSlotId"] = "13";
    map["remoteUbpuId"] = "14";
    map["remoteIouId"] = "15";
    topology::node::Port obj;
    topology::node::DataMapToObj(map, obj);
    EXPECT_EQ(obj.portId, 7u);
    EXPECT_EQ(obj.portCna, "pcna");
    EXPECT_EQ(obj.primaryCna, "cna");
    EXPECT_EQ(obj.deviceId, 11u);
    EXPECT_EQ(obj.portState, topology::node::PortState::UP);
    ASSERT_TRUE(obj.remotePortId.has_value());
    EXPECT_EQ(*obj.remotePortId, 8u);
    ASSERT_TRUE(obj.remoteDeviceId.has_value());
    EXPECT_EQ(*obj.remoteDeviceId, 12u);
    ASSERT_TRUE(obj.remoteSlotId.has_value());
    EXPECT_EQ(*obj.remoteSlotId, 13u);
    ASSERT_TRUE(obj.remoteUbpuId.has_value());
    EXPECT_EQ(*obj.remoteUbpuId, 14u);
    ASSERT_TRUE(obj.remoteIouId.has_value());
    EXPECT_EQ(*obj.remoteIouId, 15u);
}
