#include "urma_0206_bdp_vjfce_info_table_add_exist_node_map.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0206BdpVjfceInfoTableAddExistNodeMap> g_urma("urma_0206");

bool Urma0206BdpVjfceInfoTableAddExistNodeMap::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"exist node in map."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0206BdpVjfceInfoTableAddExistNodeMap::GetName() const
{
    return "bdp_vjfce_info_table_add exist node in map.";
}

std::string Urma0206BdpVjfceInfoTableAddExistNodeMap::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-EEXIST";
}

RootCause Urma0206BdpVjfceInfoTableAddExistNodeMap::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0206BdpVjfceInfoTableAddExistNodeMap::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0206BdpVjfceInfoTableAddExistNodeMap::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：exist node in map.";
}

std::string Urma0206BdpVjfceInfoTableAddExistNodeMap::GetId() const
{
    return "urma_0206";
}
} // namespace diag
