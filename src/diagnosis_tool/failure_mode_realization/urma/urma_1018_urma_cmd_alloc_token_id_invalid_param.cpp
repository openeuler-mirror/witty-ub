#include "urma_1018_urma_cmd_alloc_token_id_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1018UrmaCmdAllocTokenIdInvalidParam> g_urma("urma_1018");

bool Urma1018UrmaCmdAllocTokenIdInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1018UrmaCmdAllocTokenIdInvalidParam::GetName() const
{
    return "urma_cmd_alloc_token_id 参数非法";
}

std::string Urma1018UrmaCmdAllocTokenIdInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || token_id == NULL`；该路径返回 -1";
}

RootCause Urma1018UrmaCmdAllocTokenIdInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1018UrmaCmdAllocTokenIdInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1018UrmaCmdAllocTokenIdInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1018UrmaCmdAllocTokenIdInvalidParam::GetId() const
{
    return "urma_1018";
}
} // namespace diag
