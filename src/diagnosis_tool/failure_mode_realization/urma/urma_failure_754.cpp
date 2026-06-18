#include "urma_failure_754.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure754> g_urma("urma_754");

bool UrmaFailure754::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos && message.find("snprintf_s") != std::string::npos &&
           message.find("failed") != std::string::npos;
}

std::string UrmaFailure754::GetName() const
{
    return "打开drivers执行失败导致打开drivers失败";
}

std::string UrmaFailure754::GetRootCauseDesc() const
{
    return "urma_open_drivers执行打开drivers时依赖的打开drivers步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure754::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure754::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure754::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，snprintf_s，failed。";
}

std::string UrmaFailure754::GetId() const
{
    return "urma_754";
}
} // namespace diag
