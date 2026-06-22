#include "urma_failure_433.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure433> g_urma("urma_433");

bool UrmaFailure433::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_active_jfc, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure433::GetName() const
{
    return "去激活JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure433::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_"
           "jfc通过ioctl向驱动提交去激活JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure433::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure433::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure433::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfc，ioctl failed in urma_cmd_active_jfc, ret:，, "
           "errno:。";
}

std::string UrmaFailure433::GetId() const
{
    return "urma_433";
}
} // namespace diag
