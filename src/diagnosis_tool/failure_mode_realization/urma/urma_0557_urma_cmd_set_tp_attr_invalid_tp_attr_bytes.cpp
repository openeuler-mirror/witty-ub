#include "urma_0557_urma_cmd_set_tp_attr_invalid_tp_attr_bytes.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes> g_urma("urma_0557");

bool Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid tp_attr bytes."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::GetName() const
{
    return "urma_cmd_set_tp_attr Invalid tp_attr bytes.";
}

std::string Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `sizeof(urma_tp_attr_value_t) != sizeof(arg.in.tp_attr)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid tp_attr bytes.";
}

std::string Urma0557UrmaCmdSetTpAttrInvalidTpAttrBytes::GetId() const
{
    return "urma_0557";
}
} // namespace diag
