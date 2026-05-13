#include "urma_0498_urma_cmd_get_tp_attr_failed_ioctl_get_tp_attr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr> g_urma("urma_0498");

bool Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed in ioctl get_tp_attr, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::GetName() const
{
    return "urma_cmd_get_tp_attr Failed in ioctl get_tp_attr, ret: %.";
}

std::string Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed in ioctl get_tp_attr, ret: %.";
}

std::string Urma0498UrmaCmdGetTpAttrFailedIoctlGetTpAttr::GetId() const
{
    return "urma_0498";
}
} // namespace diag
