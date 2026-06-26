#include "urma_failure_663.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure663> g_urma("urma_663");

bool UrmaFailure663::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos &&
           message.find("Failed to open liburma dir") != std::string::npos;
}

std::string UrmaFailure663::GetName() const
{
    return "sysfs路径信息读取或解析失败导致打开drivers失败";
}

std::string UrmaFailure663::GetRootCauseDesc() const
{
    return "urma_open_"
           "drivers需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure663::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure663::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure663::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，Failed to open liburma dir。";
}

std::string UrmaFailure663::GetId() const
{
    return "urma_663";
}
} // namespace diag
