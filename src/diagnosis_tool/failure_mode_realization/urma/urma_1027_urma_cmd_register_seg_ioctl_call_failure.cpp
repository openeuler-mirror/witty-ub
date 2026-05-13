#include "urma_1027_urma_cmd_register_seg_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1027UrmaCmdRegisterSegIoctlCallFailure> g_urma("urma_1027");

bool Urma1027UrmaCmdRegisterSegIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_register_seg, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1027UrmaCmdRegisterSegIoctlCallFailure::GetName() const
{
    return "urma_cmd_register_seg ioctl调用失败";
}

std::string Urma1027UrmaCmdRegisterSegIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1027UrmaCmdRegisterSegIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1027UrmaCmdRegisterSegIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1027UrmaCmdRegisterSegIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_register_seg, ret:%, errno:%.";
}

std::string Urma1027UrmaCmdRegisterSegIoctlCallFailure::GetId() const
{
    return "urma_1027";
}
} // namespace diag
