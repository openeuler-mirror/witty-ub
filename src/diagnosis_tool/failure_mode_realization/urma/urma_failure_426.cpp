#include "urma_failure_426.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure426> g_urma("urma_426");

bool UrmaFailure426::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfc_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_set_jfc_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure426::GetName() const
{
    return "设置JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure426::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfc_"
           "opt通过ioctl向驱动提交设置JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure426::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure426::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure426::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfc_opt，ioctl failed in urma_cmd_set_jfc_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure426::GetId() const
{
    return "urma_426";
}
} // namespace diag
