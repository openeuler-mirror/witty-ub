#include "urma_0971_urma_parse_port_attr_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0971UrmaParsePortAttrPathFailure> g_urma("urma_0971");

bool Urma0971UrmaParsePortAttrPathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf failed, path: %, port_num:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0971UrmaParsePortAttrPathFailure::GetName() const
{
    return "urma_parse_port_attr 格式化路径失败";
}

std::string Urma0971UrmaParsePortAttrPathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误";
}

RootCause Urma0971UrmaParsePortAttrPathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0971UrmaParsePortAttrPathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0971UrmaParsePortAttrPathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf failed, path: %, port_num:%.";
}

std::string Urma0971UrmaParsePortAttrPathFailure::GetId() const
{
    return "urma_0971";
}
} // namespace diag
