#include "urma_failure_046.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure046> g_urma("urma_046");

bool UrmaFailure046::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos &&
           message.find("Failed to open provider") != std::string::npos;
}

std::string UrmaFailure046::GetName() const
{
    return "sysfs路径信息读取或解析失败导致打开drivers失败";
}

std::string UrmaFailure046::GetRootCauseDesc() const
{
    return "urma_open_"
           "drivers需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure046::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure046::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure046::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，Failed to open provider。";
}

std::string UrmaFailure046::GetId() const
{
    return "urma_046";
}
} // namespace diag
