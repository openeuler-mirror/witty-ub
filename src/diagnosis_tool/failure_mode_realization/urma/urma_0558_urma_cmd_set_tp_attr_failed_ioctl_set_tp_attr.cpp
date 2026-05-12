#include "urma_0558_urma_cmd_set_tp_attr_failed_ioctl_set_tp_attr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr> g_urma("urma_0558");

bool Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed in ioctl set_tp_attr, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::GetName() const
{
    return "urma_cmd_set_tp_attr Failed in ioctl set_tp_attr, ret: %.";
}

std::string Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed in ioctl set_tp_attr, ret: %.";
}

std::string Urma0558UrmaCmdSetTpAttrFailedIoctlSetTpAttr::GetId() const
{
    return "urma_0558";
}
} // namespace diag
