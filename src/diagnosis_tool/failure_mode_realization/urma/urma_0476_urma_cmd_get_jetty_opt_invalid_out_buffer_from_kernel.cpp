#include "urma_0476_urma_cmd_get_jetty_opt_invalid_out_buffer_from_kernel.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel> g_urma("urma_0476");

bool Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid out buffer from kernel."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::GetName() const
{
    return "urma_cmd_get_jetty_opt Invalid out buffer from kernel.";
}

std::string Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.buf == 0 || arg.out.len == 0 || arg.out.len > len`；该路径返回 -1";
}

RootCause Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid out buffer from kernel.";
}

std::string Urma0476UrmaCmdGetJettyOptInvalidOutBufferFromKernel::GetId() const
{
    return "urma_0476";
}
} // namespace diag
