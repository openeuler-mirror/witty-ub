#include "urma_1229_urma_str_eid_format_error.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1229UrmaStrEidFormatError> g_urma("urma_1229");

bool Urma1229UrmaStrEidFormatError::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"format error: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1229UrmaStrEidFormatError::GetName() const
{
    return "urma_str_to_eid format error: %.";
}

std::string Urma1229UrmaStrEidFormatError::GetRootCauseDesc() const
{
    return "解析设备属性、EID、sysfs 字段或输入格式失败，通常表示输入/设备上报内容不符合预期；该路径返回 -EINVAL";
}

RootCause Urma1229UrmaStrEidFormatError::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1229UrmaStrEidFormatError::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1229UrmaStrEidFormatError::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：format error: %.";
}

std::string Urma1229UrmaStrEidFormatError::GetId() const
{
    return "urma_1229";
}
} // namespace diag
