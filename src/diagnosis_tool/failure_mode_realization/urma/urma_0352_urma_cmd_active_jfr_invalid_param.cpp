#include "urma_0352_urma_cmd_active_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0352UrmaCmdActiveJfrInvalidParam> g_urma("urma_0352");

bool Urma0352UrmaCmdActiveJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0352UrmaCmdActiveJfrInvalidParam::GetName() const
{
    return "urma_cmd_active_jfr 参数非法";
}

std::string Urma0352UrmaCmdActiveJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || jfr->urma_ctx == NULL || jfr->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0352UrmaCmdActiveJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0352UrmaCmdActiveJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0352UrmaCmdActiveJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0352UrmaCmdActiveJfrInvalidParam::GetId() const
{
    return "urma_0352";
}
} // namespace diag
