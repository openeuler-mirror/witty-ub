#include "urma_1151_urma_free_token_id_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1151UrmaFreeTokenIdInvalidParam> g_urma("urma_1151");

bool Urma1151UrmaFreeTokenIdInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1151UrmaFreeTokenIdInvalidParam::GetName() const
{
    return "urma_free_token_id 参数非法";
}

std::string Urma1151UrmaFreeTokenIdInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `token_id == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1151UrmaFreeTokenIdInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1151UrmaFreeTokenIdInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1151UrmaFreeTokenIdInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1151UrmaFreeTokenIdInvalidParam::GetId() const
{
    return "urma_1151";
}
} // namespace diag
