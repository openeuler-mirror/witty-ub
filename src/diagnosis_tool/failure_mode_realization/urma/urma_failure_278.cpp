#include "urma_failure_278.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure278> g_urma("urma_278");

bool UrmaFailure278::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos &&
           message.find("Failed to get dl addr:") != std::string::npos;
}

std::string UrmaFailure278::GetName() const
{
    return "下层查询返回失败导致打开drivers失败";
}

std::string UrmaFailure278::GetRootCauseDesc() const
{
    return "urma_open_drivers需要从provider、驱动或缓存中获取drivers状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure278::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure278::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure278::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，Failed to get dl addr:。";
}

std::string UrmaFailure278::GetId() const
{
    return "urma_278";
}
} // namespace diag
