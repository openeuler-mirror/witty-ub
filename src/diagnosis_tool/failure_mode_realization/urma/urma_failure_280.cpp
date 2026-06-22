#include "urma_failure_280.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure280> g_urma("urma_280");

bool UrmaFailure280::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_eid_list") != std::string::npos && message.find("max eid cnt") != std::string::npos &&
           message.find("is err") != std::string::npos;
}

std::string UrmaFailure280::GetName() const
{
    return "EID、列表状态不满足要求导致获取EID、列表失败";
}

std::string UrmaFailure280::GetRootCauseDesc() const
{
    return "urma_get_eid_list执行获取EID、列表时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure280::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure280::GetFixSuggDesc() const
{
    return "lsmod | grep udma；urma_admin show -a 查看UB设备是否存在，部署完成后重试";
}

std::string UrmaFailure280::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_eid_list，max eid cnt，is err。";
}

std::string UrmaFailure280::GetId() const
{
    return "urma_280";
}
} // namespace diag
