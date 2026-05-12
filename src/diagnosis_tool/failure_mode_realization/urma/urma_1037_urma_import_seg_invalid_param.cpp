#include "urma_1037_urma_import_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1037UrmaImportSegInvalidParam> g_urma("urma_1037");

bool Urma1037UrmaImportSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1037UrmaImportSegInvalidParam::GetName() const
{
    return "urma_import_seg 参数非法";
}

std::string Urma1037UrmaImportSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || seg == NULL`；该路径返回 NULL";
}

RootCause Urma1037UrmaImportSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1037UrmaImportSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1037UrmaImportSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1037UrmaImportSegInvalidParam::GetId() const
{
    return "urma_1037";
}
} // namespace diag
