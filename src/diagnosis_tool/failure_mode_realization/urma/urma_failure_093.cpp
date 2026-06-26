#include "urma_failure_093.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure093> g_urma("urma_093");

bool UrmaFailure093::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_tp_attr") != std::string::npos &&
           message.find("Failed in ioctl get_tp_attr, ret:") != std::string::npos;
}

std::string UrmaFailure093::GetName() const
{
    return "获取TP、ATTR ioctl驱动命令返回失败";
}

std::string UrmaFailure093::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_"
           "attr通过ioctl向驱动提交获取TP、ATTR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure093::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure093::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure093::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_attr，Failed in ioctl get_tp_attr, ret:。";
}

std::string UrmaFailure093::GetId() const
{
    return "urma_093";
}
} // namespace diag
