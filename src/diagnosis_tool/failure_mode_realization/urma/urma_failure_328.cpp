#include "urma_failure_328.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure328> g_urma("urma_328");

bool UrmaFailure328::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_token_id_ex") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_alloc_token_id, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure328::GetName() const
{
    return "Token ID、ID临时结构分配失败导致分配Token ID、ID失败";
}

std::string UrmaFailure328::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_token_id_ex执行分配Token ID、ID前需要准备Token "
           "ID、ID临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure328::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure328::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure328::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_token_id_ex，ioctl failed in urma_cmd_alloc_token_id, "
           "ret:，, er"
           "rno:。";
}

std::string UrmaFailure328::GetId() const
{
    return "urma_328";
}
} // namespace diag
