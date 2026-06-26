#include "urma_failure_326.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure326> g_urma("urma_326");

bool UrmaFailure326::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_token_id") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_alloc_token_id, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure326::GetName() const
{
    return "Token ID、ID临时结构分配失败导致分配Token ID、ID失败";
}

std::string UrmaFailure326::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_token_id执行分配Token ID、ID前需要准备Token "
           "ID、ID临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure326::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure326::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure326::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_token_id，ioctl failed in urma_cmd_alloc_token_id, "
           "ret:，, errno"
           ":。";
}

std::string UrmaFailure326::GetId() const
{
    return "urma_326";
}
} // namespace diag
