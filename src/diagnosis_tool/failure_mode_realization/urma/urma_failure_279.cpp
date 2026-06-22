#include "urma_failure_279.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure279> g_urma("urma_279");

bool UrmaFailure279::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_device_list") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure279::GetName() const
{
    return "num_devices无效导致获取设备、列表失败";
}

std::string UrmaFailure279::GetRootCauseDesc() const
{
    return "urma_get_device_list用于获取设备、列表，调用方传入的num_devices不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure279::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure279::GetFixSuggDesc() const
{
    return "lsmod | grep udma；urma_admin show -a 查看UB设备是否存在，部署完成后重试";
}

std::string UrmaFailure279::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_device_list，Invalid parameter.。";
}

std::string UrmaFailure279::GetId() const
{
    return "urma_279";
}
} // namespace diag
