#include "urma_0575_urma_cmd_wait_jfc_faile_wait_jfc_non_block_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet> g_urma("urma_0575");

bool Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Faile to wait jfc non-block, ret: %, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::GetName() const
{
    return "urma_cmd_wait_jfc Faile to wait jfc non-block, ret: %,";
}

std::string Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `time_out == 0 && errno != EAGAIN`；该路径返回 -1";
}

RootCause Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Faile to wait jfc non-block, ret: %, errno: %.";
}

std::string Urma0575UrmaCmdWaitJfcFaileWaitJfcNonBlockRet::GetId() const
{
    return "urma_0575";
}
} // namespace diag
