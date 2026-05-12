#include "urma_0899_create_topo_map_topo_info_doesn_t_have_cur_node.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode> g_urma("urma_0899");

bool Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"topo info doesn't have cur_node"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::GetName() const
{
    return "create_topo_map topo info doesn't have cur_node";
}

std::string Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cur_node_idx == UINT32_MAX`；该路径返回 NULL";
}

RootCause Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：topo info doesn't have cur_node";
}

std::string Urma0899CreateTopoMapTopoInfoDoesnTHaveCurNode::GetId() const
{
    return "urma_0899";
}
} // namespace diag
