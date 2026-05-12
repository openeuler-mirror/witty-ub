#include "urma_0487_urma_cmd_get_jfr_opt_invalid_out_buffer_from_kernel.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel> g_urma("urma_0487");

bool Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid out buffer from kernel."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::GetName() const
{
    return "urma_cmd_get_jfr_opt Invalid out buffer from kernel.";
}

std::string Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.buf == 0 || arg.out.len == 0`；该路径返回 -1";
}

RootCause Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid out buffer from kernel.";
}

std::string Urma0487UrmaCmdGetJfrOptInvalidOutBufferFromKernel::GetId() const
{
    return "urma_0487";
}
} // namespace diag
