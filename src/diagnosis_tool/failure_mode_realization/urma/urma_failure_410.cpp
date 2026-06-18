#include "urma_failure_410.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure410> g_urma("urma_410");

bool UrmaFailure410::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_modify_jfc, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure410::GetName() const
{
    return "修改JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure410::GetRootCauseDesc() const
{
    return "urma_cmd_modify_"
           "jfc通过ioctl向驱动提交修改JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure410::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure410::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure410::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfc，ioctl failed in urma_cmd_modify_jfc, ret:，, "
           "errno:。";
}

std::string UrmaFailure410::GetId() const
{
    return "urma_410";
}
} // namespace diag
