#include "urma_failure_090.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure090> g_urma("urma_090");

bool UrmaFailure090::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_tp_attr") != std::string::npos &&
           message.find("Failed in ioctl set_tp_attr, ret:") != std::string::npos;
}

std::string UrmaFailure090::GetName() const
{
    return "设置TP、ATTR ioctl驱动命令返回失败";
}

std::string UrmaFailure090::GetRootCauseDesc() const
{
    return "urma_cmd_set_tp_"
           "attr通过ioctl向驱动提交设置TP、ATTR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure090::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure090::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure090::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_tp_attr，Failed in ioctl set_tp_attr, ret:。";
}

std::string UrmaFailure090::GetId() const
{
    return "urma_090";
}
} // namespace diag
