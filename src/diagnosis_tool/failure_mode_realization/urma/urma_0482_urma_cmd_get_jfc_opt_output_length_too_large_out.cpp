#include "urma_0482_urma_cmd_get_jfc_opt_output_length_too_large_out.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut> g_urma("urma_0482");

bool Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"output length too large, out.len=%, buf.len=%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::GetName() const
{
    return "urma_cmd_get_jfc_opt output length too large, out.len=%,";
}

std::string Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.len > len`；该路径返回 -1";
}

RootCause Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：output length too large, out.len=%, buf.len=%";
}

std::string Urma0482UrmaCmdGetJfcOptOutputLengthTooLargeOut::GetId() const
{
    return "urma_0482";
}
} // namespace diag
