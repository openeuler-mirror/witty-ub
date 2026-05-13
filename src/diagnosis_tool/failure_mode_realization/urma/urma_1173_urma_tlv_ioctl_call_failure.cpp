#include "urma_1173_urma_tlv_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1173UrmaTlvIoctlCallFailure> g_urma("urma_1173");

bool Urma1173UrmaTlvIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed, ret:%, errno:%, cmd:%, kdrv_err: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1173UrmaTlvIoctlCallFailure::GetName() const
{
    return "urma_tlv_ioctl ioctl调用失败";
}

std::string Urma1173UrmaTlvIoctlCallFailure::GetRootCauseDesc() const
{
    return "URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生在"
           "内核态驱动；用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/"
           "参数不满足要求；该路径返回 ret";
}

RootCause Urma1173UrmaTlvIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1173UrmaTlvIoctlCallFailure::GetFixSuggDesc() const
{
    return "UDMA驱动相关，需进一步排查硬件";
}

std::string Urma1173UrmaTlvIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed, ret:%, errno:%, cmd:%, kdrv_err: %.";
}

std::string Urma1173UrmaTlvIoctlCallFailure::GetId() const
{
    return "urma_1173";
}
} // namespace diag
