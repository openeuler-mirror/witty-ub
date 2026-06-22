#include "urma_failure_533.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure533> g_urma("urma_533");

bool UrmaFailure533::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jfs") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_deactive_jfs, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure533::GetName() const
{
    return "去激活JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure533::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_"
           "jfs通过ioctl向驱动提交去激活JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure533::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure533::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure533::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfs，ioctl failed in urma_cmd_deactive_jfs, ret:，, "
           "errno:。";
}

std::string UrmaFailure533::GetId() const
{
    return "urma_533";
}
} // namespace diag
