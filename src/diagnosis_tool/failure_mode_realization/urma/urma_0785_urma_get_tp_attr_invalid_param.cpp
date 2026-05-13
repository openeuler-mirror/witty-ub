#include "urma_0785_urma_get_tp_attr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0785UrmaGetTpAttrInvalidParam> g_urma("urma_0785");

bool Urma0785UrmaGetTpAttrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0785UrmaGetTpAttrInvalidParam::GetName() const
{
    return "urma_get_tp_attr 参数非法";
}

std::string Urma0785UrmaGetTpAttrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || tp_attr_cnt == NULL || tp_attr_bitmap == NULL || tp_attr == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0785UrmaGetTpAttrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0785UrmaGetTpAttrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0785UrmaGetTpAttrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0785UrmaGetTpAttrInvalidParam::GetId() const
{
    return "urma_0785";
}
} // namespace diag
