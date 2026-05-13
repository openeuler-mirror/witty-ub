#include "urma_1138_urma_cmd_free_token_id_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1138UrmaCmdFreeTokenIdInvalidParam> g_urma("urma_1138");

bool Urma1138UrmaCmdFreeTokenIdInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1138UrmaCmdFreeTokenIdInvalidParam::GetName() const
{
    return "urma_cmd_free_token_id 参数非法";
}

std::string Urma1138UrmaCmdFreeTokenIdInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `token_id == NULL || token_id->urma_ctx == NULL || token_id->urma_ctx->dev_fd "
           "< 0`；该路径返回 -1";
}

RootCause Urma1138UrmaCmdFreeTokenIdInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1138UrmaCmdFreeTokenIdInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1138UrmaCmdFreeTokenIdInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1138UrmaCmdFreeTokenIdInvalidParam::GetId() const
{
    return "urma_1138";
}
} // namespace diag
