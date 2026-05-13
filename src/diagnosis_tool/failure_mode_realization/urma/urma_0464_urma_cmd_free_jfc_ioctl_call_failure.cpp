#include "urma_0464_urma_cmd_free_jfc_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0464UrmaCmdFreeJfcIoctlCallFailure> g_urma("urma_0464");

bool Urma0464UrmaCmdFreeJfcIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_delete_jfc , ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0464UrmaCmdFreeJfcIoctlCallFailure::GetName() const
{
    return "urma_cmd_free_jfc ioctl调用失败";
}

std::string Urma0464UrmaCmdFreeJfcIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0464UrmaCmdFreeJfcIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0464UrmaCmdFreeJfcIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0464UrmaCmdFreeJfcIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_delete_jfc , ret:%, errno:%.";
}

std::string Urma0464UrmaCmdFreeJfcIoctlCallFailure::GetId() const
{
    return "urma_0464";
}
} // namespace diag
