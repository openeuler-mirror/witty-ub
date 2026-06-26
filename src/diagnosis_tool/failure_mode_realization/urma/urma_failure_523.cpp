#include "urma_failure_523.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure523> g_urma("urma_523");

bool UrmaFailure523::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure523::GetName() const
{
    return "删除JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure523::GetRootCauseDesc() const
{
    return "urma_cmd_delete_"
           "jfs通过ioctl向驱动提交删除JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure523::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure523::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure523::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure523::GetId() const
{
    return "urma_523";
}
} // namespace diag
