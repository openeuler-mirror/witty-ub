#include "urma_1002_bdp_r_v2p_token_id_del_idx_lockless_failed_find.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind> g_urma("urma_1002");

bool Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to find node, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::GetName() const
{
    return "bdp_r_v2p_token_id_del_idx_lockless Failed to find node, index: %.";
}

std::string Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 -1";
}

RootCause Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to find node, index: %.";
}

std::string Urma1002BdpRV2pTokenIdDelIdxLocklessFailedFind::GetId() const
{
    return "urma_1002";
}
} // namespace diag
