#include "urma_failure_330.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure330> g_urma("urma_330");

bool UrmaFailure330::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_token_id") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure330::GetName() const
{
    return "释放Token ID、ID ioctl驱动命令返回失败";
}

std::string UrmaFailure330::GetRootCauseDesc() const
{
    return "urma_cmd_free_token_id通过ioctl向驱动提交释放Token "
           "ID、ID命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure330::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure330::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure330::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_token_id，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure330::GetId() const
{
    return "urma_330";
}
} // namespace diag
