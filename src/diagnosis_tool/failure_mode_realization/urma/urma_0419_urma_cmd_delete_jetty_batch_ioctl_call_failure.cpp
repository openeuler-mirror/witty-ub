#include "urma_0419_urma_cmd_delete_jetty_batch_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure> g_urma("urma_0419");

bool Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_delete_jetty_batch , ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::GetName() const
{
    return "urma_cmd_delete_jetty_batch ioctl调用失败";
}

std::string Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求";
}

RootCause Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_delete_jetty_batch , ret:%, errno:%.";
}

std::string Urma0419UrmaCmdDeleteJettyBatchIoctlCallFailure::GetId() const
{
    return "urma_0419";
}
} // namespace diag
