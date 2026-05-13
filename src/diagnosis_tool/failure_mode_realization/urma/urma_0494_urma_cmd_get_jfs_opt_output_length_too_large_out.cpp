#include "urma_0494_urma_cmd_get_jfs_opt_output_length_too_large_out.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut> g_urma("urma_0494");

bool Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"output length too large, out.len=%, buf.len=%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::GetName() const
{
    return "urma_cmd_get_jfs_opt output length too large, out.len=%,";
}

std::string Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.len > len`；该路径返回 -1";
}

RootCause Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：output length too large, out.len=%, buf.len=%";
}

std::string Urma0494UrmaCmdGetJfsOptOutputLengthTooLargeOut::GetId() const
{
    return "urma_0494";
}
} // namespace diag
