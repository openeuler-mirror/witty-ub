#include "urma_failure_412.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure412> g_urma("urma_412");

bool UrmaFailure412::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_delete_jfc , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure412::GetName() const
{
    return "删除JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure412::GetRootCauseDesc() const
{
    return "urma_cmd_delete_"
           "jfc通过ioctl向驱动提交删除JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure412::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure412::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure412::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc，ioctl failed in urma_cmd_delete_jfc , ret:，, "
           "errno:。";
}

std::string UrmaFailure412::GetId() const
{
    return "urma_412";
}
} // namespace diag
