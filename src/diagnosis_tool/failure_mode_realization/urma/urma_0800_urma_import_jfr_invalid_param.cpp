#include "urma_0800_urma_import_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0800UrmaImportJfrInvalidParam> g_urma("urma_0800");

bool Urma0800UrmaImportJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0800UrmaImportJfrInvalidParam::GetName() const
{
    return "urma_import_jfr 参数非法";
}

std::string Urma0800UrmaImportJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == NULL || ctx->ops "
           "== NULL || rjfr == NULL`；该路径返回 NULL";
}

RootCause Urma0800UrmaImportJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0800UrmaImportJfrInvalidParam::GetFixSuggDesc() const
{
    return "UDMA错误定界；建链交换信息失败，可重试";
}

std::string Urma0800UrmaImportJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0800UrmaImportJfrInvalidParam::GetId() const
{
    return "urma_0800";
}
} // namespace diag
