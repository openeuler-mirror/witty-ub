#include "kvcache_conn_fault_002_001.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<KvcacheConnFault002_001> g_kvcacheconnfault("kvcache_conn_fault_002_001");

bool KvcacheConnFault002_001::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("The objectKey is empty") != std::string::npos ||
           message.find("dataSize should be bigger than zero") != std::string::npos ||
           message.find("length not match") != std::string::npos;
}

std::string KvcacheConnFault002_001::GetName() const
{
    return "respMsg参数非法类故障";
}

std::string KvcacheConnFault002_001::GetRootCauseDesc() const
{
    return "业务参数非法，属于用户侧问题。（来源：08手册:L247）";
}

RootCause KvcacheConnFault002_001::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_001::GetFixSuggDesc() const
{
    return "业务方校验调用参数。（来源：08手册:L247）";
}

std::string KvcacheConnFault002_001::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（来源：08手册:L246-249）：匹配The objectKey is empty / dataSize should be bigger than "
           "zero / length not match。（来源：08手册:L247）";
}

std::string KvcacheConnFault002_001::GetId() const
{
    return "kvcache_conn_fault_002_001";
}
}