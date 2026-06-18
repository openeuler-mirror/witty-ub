#include "urma_failure_344.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure344> g_urma("urma_344");

bool UrmaFailure344::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_token_id_ex") != std::string::npos &&
           message.find("dev not support token id table mode.") != std::string::npos;
}

std::string UrmaFailure344::GetName() const
{
    return "provider未提供_t操作实现导致分配Token ID、ID失败";
}

std::string UrmaFailure344::GetRootCauseDesc() const
{
    return "urma_alloc_token_id_ex需要通过provider操作表完成分配Token "
           "ID、ID，当前设备provider缺少对应回调或能力不支持该操作。";
}

RootCause UrmaFailure344::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure344::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure344::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_token_id_ex，dev not support token id table mode.。";
}

std::string UrmaFailure344::GetId() const
{
    return "urma_344";
}
} // namespace diag
