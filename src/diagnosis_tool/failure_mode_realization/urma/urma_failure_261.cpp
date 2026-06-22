#include "urma_failure_261.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure261> g_urma("urma_261");

bool UrmaFailure261::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_token_id") != std::string::npos &&
           message.find("[DRV_ERR]Failed to register seg, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure261::GetName() const
{
    return "下层注册或导入返回失败导致分配Token ID、ID失败";
}

std::string UrmaFailure261::GetRootCauseDesc() const
{
    return "urma_alloc_token_id在分配Token "
           "ID、ID时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure261::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure261::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure261::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_token_id，[DRV_ERR]Failed to register seg, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure261::GetId() const
{
    return "urma_261";
}
} // namespace diag
