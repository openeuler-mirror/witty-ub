#include "urma_0792_urma_import_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0792UrmaImportJettyInvalidParam> g_urma("urma_0792");

bool Urma0792UrmaImportJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0792UrmaImportJettyInvalidParam::GetName() const
{
    return "urma_import_jetty 参数非法";
}

std::string Urma0792UrmaImportJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == NULL || ctx->ops "
           "== NULL || rjetty == NULL`；该路径返回 NULL";
}

RootCause Urma0792UrmaImportJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0792UrmaImportJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0792UrmaImportJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0792UrmaImportJettyInvalidParam::GetId() const
{
    return "urma_0792";
}
} // namespace diag
