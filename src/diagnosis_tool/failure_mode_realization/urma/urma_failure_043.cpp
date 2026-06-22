#include "urma_failure_043.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure043> g_urma("urma_043");

bool UrmaFailure043::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_provider") != std::string::npos &&
           message.find("open failed, err:") != std::string::npos;
}

std::string UrmaFailure043::GetName() const
{
    return "sysfs路径信息读取或解析失败导致打开provider失败";
}

std::string UrmaFailure043::GetRootCauseDesc() const
{
    return "urma_open_"
           "provider需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure043::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure043::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure043::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_provider，open failed, err:。";
}

std::string UrmaFailure043::GetId() const
{
    return "urma_043";
}
} // namespace diag
