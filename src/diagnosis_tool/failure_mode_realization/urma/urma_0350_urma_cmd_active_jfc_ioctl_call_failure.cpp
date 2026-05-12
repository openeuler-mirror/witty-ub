#include "urma_0350_urma_cmd_active_jfc_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0350UrmaCmdActiveJfcIoctlCallFailure> g_urma("urma_0350");

bool Urma0350UrmaCmdActiveJfcIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_active_jfc, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0350UrmaCmdActiveJfcIoctlCallFailure::GetName() const
{
    return "urma_cmd_active_jfc ioctl调用失败";
}

std::string Urma0350UrmaCmdActiveJfcIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0350UrmaCmdActiveJfcIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0350UrmaCmdActiveJfcIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0350UrmaCmdActiveJfcIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_active_jfc, ret:%, errno:%.";
}

std::string Urma0350UrmaCmdActiveJfcIoctlCallFailure::GetId() const
{
    return "urma_0350";
}
} // namespace diag
