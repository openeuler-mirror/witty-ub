#include "urma_1019_urma_cmd_alloc_token_id_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1019UrmaCmdAllocTokenIdIoctlCallFailure> g_urma("urma_1019");

bool Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_alloc_token_id, ret:%, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::GetName() const
{
    return "urma_cmd_alloc_token_id ioctl调用失败";
}

std::string Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_alloc_token_id, ret:%, errno: %.";
}

std::string Urma1019UrmaCmdAllocTokenIdIoctlCallFailure::GetId() const
{
    return "urma_1019";
}
} // namespace diag
