#include "urma_0518_urma_cmd_modify_jfr_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0518UrmaCmdModifyJfrIoctlCallFailure> g_urma("urma_0518");

bool Urma0518UrmaCmdModifyJfrIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_modify_jfr, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0518UrmaCmdModifyJfrIoctlCallFailure::GetName() const
{
    return "urma_cmd_modify_jfr ioctl调用失败";
}

std::string Urma0518UrmaCmdModifyJfrIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0518UrmaCmdModifyJfrIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0518UrmaCmdModifyJfrIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0518UrmaCmdModifyJfrIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_modify_jfr, ret:%, errno:%.";
}

std::string Urma0518UrmaCmdModifyJfrIoctlCallFailure::GetId() const
{
    return "urma_0518";
}
} // namespace diag
