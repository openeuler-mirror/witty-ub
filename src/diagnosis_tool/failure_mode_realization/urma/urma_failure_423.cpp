#include "urma_failure_423.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure423> g_urma("urma_423");

bool UrmaFailure423::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_delete_jfc , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure423::GetName() const
{
    return "释放JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure423::GetRootCauseDesc() const
{
    return "urma_cmd_free_"
           "jfc通过ioctl向驱动提交释放JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure423::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure423::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure423::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfc，ioctl failed in urma_cmd_delete_jfc , ret:，, "
           "errno:。";
}

std::string UrmaFailure423::GetId() const
{
    return "urma_423";
}
} // namespace diag
