#include "urma_0493_urma_cmd_get_jfs_opt_invalid_out_buffer_from_kernel.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel> g_urma("urma_0493");

bool Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid out buffer from kernel."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::GetName() const
{
    return "urma_cmd_get_jfs_opt Invalid out buffer from kernel.";
}

std::string Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.buf == 0 || arg.out.len == 0`；该路径返回 -1";
}

RootCause Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid out buffer from kernel.";
}

std::string Urma0493UrmaCmdGetJfsOptInvalidOutBufferFromKernel::GetId() const
{
    return "urma_0493";
}
} // namespace diag
