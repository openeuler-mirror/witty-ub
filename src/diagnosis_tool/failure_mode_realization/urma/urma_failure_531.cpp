#include "urma_failure_531.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure531> g_urma("urma_531");

bool UrmaFailure531::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfs") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_free_jfs , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure531::GetName() const
{
    return "释放JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure531::GetRootCauseDesc() const
{
    return "urma_cmd_free_"
           "jfs通过ioctl向驱动提交释放JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure531::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure531::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure531::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfs，ioctl failed in urma_cmd_free_jfs , ret:，, errno:。";
}

std::string UrmaFailure531::GetId() const
{
    return "urma_531";
}
} // namespace diag
