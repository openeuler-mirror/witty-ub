#include "urma_1001_bdp_r_v2p_token_id_del_idx_lockless_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure> g_urma("urma_1001");

bool Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1002"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::GetName() const
{
    return "bdp_r_v2p_token_id_del_idx_lockless 函数故障";
}

std::string Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1001BdpRV2pTokenIdDelIdxLocklessFunctionFailure::GetId() const
{
    return "urma_1001";
}
} // namespace diag
