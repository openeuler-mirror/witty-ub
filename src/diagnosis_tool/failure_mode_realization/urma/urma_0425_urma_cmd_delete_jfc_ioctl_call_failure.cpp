#include "urma_0425_urma_cmd_delete_jfc_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0425UrmaCmdDeleteJfcIoctlCallFailure> g_urma("urma_0425");

bool Urma0425UrmaCmdDeleteJfcIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_delete_jfc , ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0425UrmaCmdDeleteJfcIoctlCallFailure::GetName() const
{
    return "urma_cmd_delete_jfc ioctl调用失败";
}

std::string Urma0425UrmaCmdDeleteJfcIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0425UrmaCmdDeleteJfcIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0425UrmaCmdDeleteJfcIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0425UrmaCmdDeleteJfcIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_delete_jfc , ret:%, errno:%.";
}

std::string Urma0425UrmaCmdDeleteJfcIoctlCallFailure::GetId() const
{
    return "urma_0425";
}
} // namespace diag
