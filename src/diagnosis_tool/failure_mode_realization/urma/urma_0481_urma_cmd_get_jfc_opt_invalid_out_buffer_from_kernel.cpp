#include "urma_0481_urma_cmd_get_jfc_opt_invalid_out_buffer_from_kernel.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel> g_urma("urma_0481");

bool Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid out buffer from kernel."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::GetName() const
{
    return "urma_cmd_get_jfc_opt Invalid out buffer from kernel.";
}

std::string Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.buf == 0 || arg.out.len == 0`；该路径返回 -1";
}

RootCause Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid out buffer from kernel.";
}

std::string Urma0481UrmaCmdGetJfcOptInvalidOutBufferFromKernel::GetId() const
{
    return "urma_0481";
}
} // namespace diag
