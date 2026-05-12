#include "urma_0528_urma_cmd_query_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0528UrmaCmdQueryJfrInvalidParam> g_urma("urma_0528");

bool Urma0528UrmaCmdQueryJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0528UrmaCmdQueryJfrInvalidParam::GetName() const
{
    return "urma_cmd_query_jfr 参数非法";
}

std::string Urma0528UrmaCmdQueryJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || jfr->urma_ctx == NULL || jfr->urma_ctx->dev_fd < 0 || cfg == "
           "NULL || attr == NULL`；该路径返回 -1";
}

RootCause Urma0528UrmaCmdQueryJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0528UrmaCmdQueryJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0528UrmaCmdQueryJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0528UrmaCmdQueryJfrInvalidParam::GetId() const
{
    return "urma_0528";
}
} // namespace diag
