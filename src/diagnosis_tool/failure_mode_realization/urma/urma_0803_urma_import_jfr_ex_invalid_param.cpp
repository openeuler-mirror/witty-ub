#include "urma_0803_urma_import_jfr_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0803UrmaImportJfrExInvalidParam> g_urma("urma_0803");

bool Urma0803UrmaImportJfrExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0803UrmaImportJfrExInvalidParam::GetName() const
{
    return "urma_import_jfr_ex 参数非法";
}

std::string Urma0803UrmaImportJfrExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || token_value == NULL || rjfr == NULL || cfg == "
           "NULL`；该路径返回 NULL";
}

RootCause Urma0803UrmaImportJfrExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0803UrmaImportJfrExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0803UrmaImportJfrExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0803UrmaImportJfrExInvalidParam::GetId() const
{
    return "urma_0803";
}
} // namespace diag
