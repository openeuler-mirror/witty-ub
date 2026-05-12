#include "urma_0496_urma_cmd_get_tp_attr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0496UrmaCmdGetTpAttrInvalidParam> g_urma("urma_0496");

bool Urma0496UrmaCmdGetTpAttrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0496UrmaCmdGetTpAttrInvalidParam::GetName() const
{
    return "urma_cmd_get_tp_attr 参数非法";
}

std::string Urma0496UrmaCmdGetTpAttrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || tp_attr_cnt == NULL || tp_attr_bitmap == NULL || tp_attr == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0496UrmaCmdGetTpAttrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0496UrmaCmdGetTpAttrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0496UrmaCmdGetTpAttrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0496UrmaCmdGetTpAttrInvalidParam::GetId() const
{
    return "urma_0496";
}
} // namespace diag
